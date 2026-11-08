"""Smoke checks for Combat Lab 0.3 (requires playwright and Chromium)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text()
html = html.replace('<link rel="stylesheet" href="src/style.css">', '<style>' + (root / "src/style.css").read_text() + '</style>')
html = html.replace('<script type="module" src="src/game.js"></script>', '<script>' + (root / "src/game.js").read_text() + '</script>')
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width":1280,"height":720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(html, wait_until="load")
    page.get_by_role("button", name="ENTRAR EN LA ARENA").click()
    page.wait_for_timeout(250)
    initial = page.evaluate("window.__humansApocalypse.getSnapshot()")
    assert initial["player"]["ammo"] == initial["player"]["mag"], "Fires without input"
    page.mouse.move(900, 400)
    page.mouse.down()
    page.wait_for_timeout(340)
    fired = page.evaluate("window.__humansApocalypse.getSnapshot()")
    assert fired["player"]["ammo"] < initial["player"]["ammo"], "Manual firing failed"
    page.mouse.up()
    page.keyboard.down("d")
    page.wait_for_timeout(250)
    page.keyboard.up("d")
    moved = page.evaluate("window.__humansApocalypse.getSnapshot()")
    assert moved["player"]["x"] > fired["player"]["x"], "Movement failed"
    page.keyboard.press("q")
    page.wait_for_timeout(60)
    assert page.evaluate("window.__humansApocalypse.getSnapshot().player.armWait") > 0
    page.keyboard.press("Escape")
    assert page.evaluate("window.__humansApocalypse.getSnapshot().state") == "paused"
    page.keyboard.press("Escape")
    assert page.evaluate("window.__humansApocalypse.getSnapshot().state") == "playing"
    assert not errors, errors
    print("Combat Lab 0.3 smoke tests passed")
    browser.close()
