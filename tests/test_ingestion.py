from app.ingestion import clean_html


def test_clean_html_removes_navigation_and_scripts():
    title, text = clean_html(
        "<html><title>Acme</title><nav>Menu</nav><main>Useful product evidence for developers.</main><script>secret()</script></html>"
    )
    assert title == "Acme"
    assert "Useful product evidence" in text
    assert "Menu" not in text and "secret" not in text
