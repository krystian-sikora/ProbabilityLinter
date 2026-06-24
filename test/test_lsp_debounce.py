import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from lsp import ProbLinterServer, compute_diagnostics


class TestComputeDiagnostics(unittest.TestCase):
    def test_valid_source_has_no_errors(self):
        source = '<prob target="m" value="0.5" />'
        diagnostics = compute_diagnostics(source)
        severities = {d.severity.name for d in diagnostics}
        self.assertNotIn("Error", severities)


class TestLspDebounce(unittest.IsolatedAsyncioTestCase):
    async def test_debounce_waits_before_lint(self):
        ls = ProbLinterServer("test", "0", debounce_seconds=0.05)
        ls.lint_and_publish = AsyncMock()

        ls.schedule_debounced_lint("file:///a.md")
        ls.schedule_debounced_lint("file:///a.md")

        await asyncio.sleep(0.01)
        ls.lint_and_publish.assert_not_called()

        await asyncio.sleep(0.06)
        ls.lint_and_publish.assert_awaited_once_with("file:///a.md")

    async def test_debounce_cancels_stale_task(self):
        ls = ProbLinterServer("test", "0", debounce_seconds=0.05)
        calls: list[str] = []

        async def record(uri: str) -> None:
            calls.append(uri)

        ls.lint_and_publish = record

        ls.schedule_debounced_lint("file:///a.md")
        await asyncio.sleep(0.03)
        ls.schedule_debounced_lint("file:///a.md")
        await asyncio.sleep(0.06)

        self.assertEqual(calls, ["file:///a.md"])

    async def test_lint_and_publish_skips_stale_version(self):
        ls = ProbLinterServer("test", "0")
        document = MagicMock(version=1, source='<prob target="m" />')
        changed = MagicMock(version=2, source=document.source)

        mock_workspace = MagicMock()
        mock_workspace.get_text_document = MagicMock(side_effect=[document, changed])
        ls.text_document_publish_diagnostics = MagicMock()

        loop = asyncio.get_running_loop()

        async def immediate(_pool, fn, *args):
            return fn(*args)

        with patch.object(ProbLinterServer, "workspace", new_callable=PropertyMock, return_value=mock_workspace):
            with patch.object(loop, "run_in_executor", side_effect=immediate):
                with patch("lsp.compute_diagnostics", return_value=[]):
                    await ls.lint_and_publish("file:///a.md")

        ls.text_document_publish_diagnostics.assert_not_called()


if __name__ == "__main__":
    unittest.main()
