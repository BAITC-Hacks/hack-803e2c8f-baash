"""Record the Pulse 109 demo in a headless Chromium tab, without desktop capture."""

from __future__ import annotations

import argparse
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

WIDTH = 1920
HEIGHT = 1080
WATER_REPORT = "После ремонта вода стала мутной и появился металлический запах."
WATER_LOCATION = "Условный квартал Алмалы, Алматы"
WEEKLY_QUESTION = "Покажи обращения за последние 7 дней в Алматы"
FORECAST_QUESTION = "Прогноз нагрузки по обращениям в Алматы на 3 месяца"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output .webm path")
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:3000", help="Running local demo base URL"
    )
    parser.add_argument("--duration", type=int, default=117, help="Video duration in seconds")
    return parser.parse_args()


def button(page: Page, name: str):
    return page.get_by_role("button", name=name, exact=True)


def click(page: Page, name: str, timeout: int = 8_000) -> None:
    target = button(page, name)
    target.wait_for(state="visible", timeout=timeout)
    target.click(timeout=timeout)


def wait_until(page: Page, started_at: float, second: float) -> None:
    remaining_ms = round((started_at + second - time.monotonic()) * 1000)
    if remaining_ms > 0:
        page.wait_for_timeout(remaining_ms)


def wait_for_scene(page: Page, name: str, timeout: int = 8_000) -> None:
    page.get_by_text(name, exact=True).first.wait_for(state="visible", timeout=timeout)


def prepare_workspace(context: BrowserContext, page: Page, base_url: str) -> float:
    context.add_init_script(
        """
        localStorage.setItem('pulse109-demo-disclosure-v1', 'accepted');
        localStorage.setItem('pulse109-sidebar-collapsed', '1');
        """
    )
    started_at = time.monotonic()
    page.goto(f"{base_url.rstrip('/')}/demo", wait_until="domcontentloaded", timeout=20_000)
    page.locator("#operations-title").wait_for(state="visible", timeout=15_000)
    button(page, "Поиск возникающих проблем").wait_for(state="visible", timeout=15_000)
    return started_at


def record_scenario(page: Page, started_at: float, duration: int) -> None:
    # Operations Center: leave enough time for the map, KPIs, and daily chart.
    wait_until(page, started_at, 8)

    # Intake: show the prefilled first screen, then jump directly to preflight.
    click(page, "Подать обращение")
    description = page.locator("#description")
    description.wait_for(state="visible", timeout=8_000)
    if description.input_value() != WATER_REPORT:
        description.fill(WATER_REPORT)
    location = page.locator("#location")
    if location.count() and not location.input_value():
        location.fill(WATER_LOCATION)
    wait_until(page, started_at, 11)
    for _ in range(4):
        click(page, "Далее")
        page.wait_for_timeout(180)
    wait_for_scene(page, "Похожие открытые проблемы")
    page.get_by_text("Похожее обращение 1", exact=False).wait_for(state="visible", timeout=8_000)
    wait_until(page, started_at, 24)
    click(page, "Подтвердить и отправить")
    wait_for_scene(page, "Обращение принято")
    wait_until(page, started_at, 27)
    click(page, "Открыть в очереди оператора")

    # Operator recommendation stays advisory until the operator confirms it.
    button(page, "Получить рекомендацию").wait_for(state="visible", timeout=10_000)
    wait_until(page, started_at, 29)
    click(page, "Получить рекомендацию")
    button(page, "Подтвердить рекомендацию").wait_for(state="visible", timeout=8_000)
    wait_until(page, started_at, 37)
    click(page, "Подтвердить рекомендацию")
    wait_until(page, started_at, 45)

    # Radar: scan, select the water cluster, and create its incident by hand.
    click(page, "Операционный центр")
    button(page, "Поиск возникающих проблем").wait_for(state="visible", timeout=10_000)
    wait_until(page, started_at, 47)
    click(page, "Поиск возникающих проблем")
    button(page, "Кластер").wait_for(state="visible", timeout=10_000)
    wait_until(page, started_at, 50)
    click(page, "Кластер")
    button(page, "Создать инцидент из кластера").wait_for(state="visible", timeout=8_000)
    wait_until(page, started_at, 58)
    click(page, "Создать инцидент из кластера")
    page.locator("#war-room-title").wait_for(state="visible", timeout=12_000)
    wait_until(page, started_at, 76)

    # Ask Pulse: keep the answer itself, its KPI row, and chart in the viewport.
    close_button = button(page, "✕")
    close_button.wait_for(state="visible", timeout=8_000)
    close_button.click()
    ask_pulse = page.locator("#ask-pulse-title")
    ask_pulse.wait_for(state="visible", timeout=8_000)
    ask_pulse.scroll_into_view_if_needed()
    wait_until(page, started_at, 80)
    page.locator("#ask-pulse-question").fill(WEEKLY_QUESTION)
    button(page, "Спросить").click()
    page.get_by_text(re.compile(r"за 7 дней найдено\s+\d+\s+обращений")).wait_for(
        state="visible", timeout=12_000
    )
    page.evaluate("window.scrollBy({ top: 360, behavior: 'instant' })")
    wait_until(page, started_at, 101)

    # Finish on the three-month forecast. Keep its headline and KPIs readable.
    button(page, "Новый вопрос").click()
    page.locator("#ask-pulse-question").fill(FORECAST_QUESTION)
    button(page, "Спросить").click()
    page.get_by_text(FORECAST_QUESTION, exact=True).first.wait_for(state="visible", timeout=12_000)
    page.locator("dd").filter(has_text=re.compile(r"1\s?703")).first.wait_for(
        state="visible", timeout=12_000
    )
    forecast_copy = page.get_by_text(FORECAST_QUESTION, exact=True).last
    forecast_copy.scroll_into_view_if_needed()
    page.evaluate("window.scrollBy({ top: 250, behavior: 'instant' })")
    wait_until(page, started_at, duration)


def main() -> None:
    args = parse_args()
    if args.duration < 30:
        raise SystemExit("duration must be at least 30 seconds")
    if args.output.suffix.lower() != ".webm":
        raise SystemExit("Playwright's browser-native recorder writes .webm files")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pulse109-browser-recording-") as recording_dir:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
                locale="ru-RU",
                record_video_dir=recording_dir,
                record_video_size={"width": WIDTH, "height": HEIGHT},
            )
            page = context.new_page()
            video = page.video
            if video is None:
                raise RuntimeError("Chromium video capture did not start")
            completed = False
            try:
                started_at = prepare_workspace(context, page, args.base_url)
                print(
                    f"Recording internal demo tab at {WIDTH}x{HEIGHT} for "
                    f"{args.duration}s -> {args.output}",
                    flush=True,
                )
                record_scenario(page, started_at, args.duration)
                completed = True
            finally:
                context.close()
                try:
                    if completed:
                        temporary_output = Path(recording_dir) / "recording.webm"
                        video.save_as(temporary_output)
                        temporary_output.replace(args.output)
                finally:
                    browser.close()

    print(f"Saved browser-only video: {args.output} ({args.output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
