"""Pramana CLI entry point."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from pramana import auth
from pramana.models import detect_provider, resolve_alias
from pramana.providers.registry import list_unavailable_hints, resolve_provider
from pramana.runner import run_eval
from pramana.storage import append_result, load_results, remove_run
from pramana.submitter import submit_results

console = Console()

# Suite directory lives inside the package
_SUITES_DIR = Path(__file__).parent / "suites" / "v1.0"


@click.group()
@click.version_option()
def cli():
    """Pramana: Crowdsourced LLM drift detection."""
    pass


@cli.command()
@click.option("--tier", type=click.Choice(["cheap", "moderate", "comprehensive"]), required=True)
@click.option(
    "--model",
    required=True,
    help="Model ID (e.g., gpt-4o, claude-opus-4-6, gemini-2.5-pro)",
)
@click.option("--output", type=click.Path(), default="results.json", help="Output file path")
@click.option("--temperature", type=float, default=0.0, help="Temperature (default: 0)")
@click.option("--seed", type=int, default=42, help="Random seed (default: 42)")
@click.option("--offline", is_flag=True, help="Save locally without submitting")
@click.option("--api-key", help="API key (or set OPENAI_API_KEY/ANTHROPIC_API_KEY/GOOGLE_API_KEY)")
@click.option(
    "--use-subscription", is_flag=True,
    help="Use Claude Code subscription (no API key needed)",
)
def run(tier, model, output, temperature, seed, offline, api_key, use_subscription):
    """Run evals against a model."""
    asyncio.run(
        _run_async(tier, model, output, temperature, seed, offline, api_key, use_subscription)
    )


async def _run_async(tier, model, output, temperature, seed, offline, api_key, use_subscription):
    """Async implementation of run command."""
    # Determine suite path
    suite_path = _SUITES_DIR / f"{tier}.jsonl"
    if not suite_path.exists():
        console.print(f"[red]Suite not found: {suite_path}[/red]")
        sys.exit(1)

    # Resolve short aliases (e.g. "opus" → "claude-opus-4-6")
    model = resolve_alias(model)

    # --- Provider selection via registry ---
    try:
        provider_name = detect_provider(model)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("\n[yellow]Run 'pramana models' to see available models[/yellow]")
        sys.exit(1)

    if api_key:
        mode = "api"
    elif use_subscription:
        mode = "subscription"
    else:
        mode = None  # auto-detect

    preferred = (auth.load_config() or {}).get("preferred_mode", "subscription")
    entry = resolve_provider(provider_name, mode=mode, api_key=api_key, preferred_mode=preferred)

    if not entry:
        hints = list_unavailable_hints(provider_name)
        console.print(f"[red]No credentials found for {model}[/red]")
        for h in hints:
            console.print(f"  {h}")
        sys.exit(1)

    if entry.mode == "subscription":
        console.print(f"[cyan]Using {entry.provider_name} subscription mode[/cyan]")
        console.print("[yellow]⚠ Subscription mode may not honor temperature/seed[/yellow]")
    else:
        console.print(f"[cyan]Using {entry.provider_name} API mode[/cyan]")

    provider = entry.cls(model_id=model, api_key=api_key)

    # Run evals
    console.print(f"[cyan]Running {tier} suite against {model}...[/cyan]")

    # Count tests upfront for progress bar
    test_count = sum(1 for line in suite_path.read_text().strip().split("\n") if line.strip())

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Running tests", total=test_count)

        def on_progress(completed: int, total: int, result) -> None:
            passed = result.assertion_result.passed
            status = "[green]pass[/green]" if passed else "[red]fail[/red]"
            desc = f"Test {result.test_id} {status}"
            progress.update(task, completed=completed, description=desc)

        results = await run_eval(
            suite_path=suite_path,
            provider=provider,
            temperature=temperature,
            seed=seed,
            on_progress=on_progress,
        )

    # Display results
    passed = results.summary.passed
    skipped = results.summary.skipped
    total = results.summary.total
    console.print(f"\n[green]✓[/green] Completed: {passed}/{total} passed")
    if skipped:
        console.print(f"[yellow]Skipped: {skipped} (unimplemented assertion types)[/yellow]")
    console.print(f"[cyan]Pass rate: {results.summary.pass_rate:.1%}[/cyan]")

    # Save results (append to existing blocks)
    output_path = Path(output)
    block_count = append_result(output_path, results)
    console.print(
        f"\n[green]Results saved to: {output_path}[/green] ({block_count} pending run(s))"
    )

    if not offline:
        console.print(
            f"\n[yellow]Note: Use 'pramana submit {output_path}' to upload results[/yellow]"
        )


@cli.command()
@click.option("--refresh", is_flag=True, help="Force refresh from upstream")
def models(refresh):
    """List available models from all providers."""
    from pramana.models import get_available_models

    console.print("[cyan]Fetching available models...[/cyan]\n")

    try:
        model_list = get_available_models(force_refresh=refresh)

        for provider, models in sorted(model_list.items()):
            console.print(f"[bold]{provider.upper()}[/bold]")
            for model in sorted(models):
                console.print(f"  • {model}")
            console.print()

        console.print(f"[green]Total: {sum(len(m) for m in model_list.values())} models[/green]")

    except Exception as e:
        console.print(f"[red]Failed to fetch models: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("results_file", type=click.Path())
@click.option(
    "--api-url", default=None,
    help=f"API endpoint URL (default: from login config or {auth.DEFAULT_API_URL})",
)
def submit(results_file, api_url):
    """Submit results to Pramana platform."""
    # Use configured API URL from login if available
    if api_url is None:
        api_url = auth.get_api_url() or auth.DEFAULT_API_URL
    asyncio.run(_submit_async(results_file, api_url))


async def _submit_async(results_file, api_url):
    """Async implementation of submit command — drains blocks one-by-one."""
    path = Path(results_file)

    if not path.exists():
        console.print("[yellow]No results file found. Run 'pramana run' first.[/yellow]")
        return

    blocks = load_results(path)

    if not blocks:
        console.print("[yellow]No results to submit. Run 'pramana run' first.[/yellow]")
        return

    total = len(blocks)
    console.print(f"[cyan]Submitting {total} run(s) to {api_url}...[/cyan]")

    total_submitted = 0
    total_duplicates = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading...", total=total)

        for i in range(total):
            # Always read index 0 — previous block was removed on success
            block = load_results(path)[0]
            model_id = block.get("run_metadata", {}).get("model_id", "unknown")
            desc = f"Uploading run {i + 1}/{total} (model: {model_id})"
            progress.update(task, description=desc)

            try:
                response = await submit_results(block, api_url)
                total_submitted += response.get("submitted", 0)
                total_duplicates += response.get("duplicates", 0)
                remove_run(path, 0)
                progress.update(task, completed=i + 1)
            except Exception as e:
                progress.stop()
                remaining = total - i
                console.print(f"[red]Submission failed on run {i + 1}: {e}[/red]")
                console.print(f"[yellow]{remaining} run(s) remain in {path}[/yellow]")
                sys.exit(1)

    console.print(f"[green]✓[/green] Submitted {total_submitted} results from {total} run(s)")

    if total_duplicates:
        console.print(f"[yellow]Note: {total_duplicates} duplicate(s) already on server[/yellow]")


@cli.command()
@click.option("--api-url", default=auth.DEFAULT_API_URL, help="API endpoint URL")
def login(api_url):
    """Log in to enable personalized tracking."""
    auth.login(api_url)


@cli.command()
def logout():
    """Log out and clear stored token."""
    auth.logout()


@cli.command()
def whoami():
    """Show current login status."""
    auth.whoami()


@cli.command()
@click.option("--prefer-api", is_flag=True, help="Default to API mode when both are available")
@click.option(
    "--prefer-subscription", is_flag=True,
    help="Default to subscription mode when both are available",
)
@click.option("--show", is_flag=True, help="Show current config")
def config(prefer_api, prefer_subscription, show):
    """Configure auto-detection preferences."""
    if show:
        cfg = auth.load_config() or {}
        mode = cfg.get("preferred_mode", "subscription (default)")
        console.print(f"preferred_mode: {mode}")
        return

    if prefer_api and prefer_subscription:
        console.print("[red]Cannot set both --prefer-api and --prefer-subscription[/red]")
        sys.exit(1)

    if prefer_api:
        auth.update_config("preferred_mode", "api")
        console.print("Preferred mode set to: api")
    elif prefer_subscription:
        auth.update_config("preferred_mode", "subscription")
        console.print("Preferred mode set to: subscription")
    else:
        console.print("Use --show, --prefer-api, or --prefer-subscription")


@cli.command()
@click.option(
    "--anonymize", is_flag=True,
    help="Keep results as anonymous instead of full deletion",
)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--api-url", default=None, help="API endpoint URL")
def delete(anonymize, confirm, api_url):
    """Delete all your data (GDPR compliance)."""
    asyncio.run(_delete_async(anonymize, confirm, api_url))


async def _delete_async(anonymize, confirm, api_url):
    """Async implementation of delete command."""
    # Check if logged in
    if not auth.load_config():
        console.print("[red]Not logged in. Nothing to delete.[/red]")
        sys.exit(1)

    # Confirm action
    if not confirm:
        if anonymize:
            message = (
                "This will:\n"
                "  • Keep your results in the crowd dataset (as anonymous)\n"
                "  • Remove the link between your account and submissions\n"
                "  • Log you out\n\n"
                "Your results will still contribute to crowd statistics.\n"
                "Continue?"
            )
        else:
            message = (
                "This will PERMANENTLY DELETE:\n"
                "  • All your submission history\n"
                "  • All your test results\n"
                "  • Your account link\n\n"
                "This CANNOT be undone. Continue?"
            )

        if not click.confirm(console.render_str(f"[yellow]{message}[/yellow]")):
            console.print("[cyan]Cancelled.[/cyan]")
            return

    # Delete via API
    try:
        response = await auth.delete_user_data(anonymize_only=anonymize, api_url=api_url)

        if response.get("status") == "anonymized":
            console.print("[green]✓[/green] Data anonymized successfully")
            console.print("Your results are now part of the anonymous crowd dataset.")
        elif response.get("status") == "deleted":
            console.print("[green]✓[/green] Data deleted successfully")
            console.print("All your submissions have been permanently removed.")
        else:
            console.print(f"[yellow]Status: {response.get('status', 'unknown')}[/yellow]")

        # Logout locally
        auth.logout()

    except Exception as e:
        console.print(f"[red]Deletion failed: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
