import unittest
import server
from src.config import BASE_URL, MATERIAL_TYPES, ASSIGN_TYPES
from src.infrastructure.moodle_parser import parse_course_page, extract_user_id, extract_visible_text
from src.presentation.mcp_tools import mcp


class TestNTierArchitecture(unittest.TestCase):
    def test_config_constants(self):
        self.assertEqual(BASE_URL, "https://classroom.its.ac.id")
        self.assertIn("resource", MATERIAL_TYPES)
        self.assertIn("assign", ASSIGN_TYPES)

    def test_user_id_parsing(self):
        sample_html = '<html><script>var M = {"userId":98765};</script></html>'
        self.assertEqual(extract_user_id(sample_html), 98765)

    def test_course_page_parsing(self):
        sample_html = """
        <li class="section">
            <h3 class="sectionname">Minggu 1</h3>
            <li class="activity resource modtype_resource">
                <span class="instancename">Slide Modul 1<span class="accesshide"> File</span></span>
                <a class="aalink" href="https://classroom.its.ac.id/mod/resource/view.php?id=12345">Link</a>
                <div class="activity-dates">Opened: 1 Jan 2026</div>
            </li>
        </li>
        """
        sections = parse_course_page(sample_html)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["section"], "Minggu 1")
        activities = sections[0]["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["cmid"], 12345)
        self.assertEqual(activities[0]["modtype"], "resource")
        self.assertEqual(activities[0]["name"], "Slide Modul 1")

    def test_visible_text_extraction(self):
        sample_html = "<div><script>alert(1);</script><p>Hello World</p></div>"
        text = extract_visible_text(sample_html, "div")
        self.assertIn("Hello World", text)
        self.assertNotIn("alert", text)

    def test_server_entrypoint_reexports(self):
        self.assertTrue(callable(server.get_profile))
        self.assertTrue(callable(server.list_courses))
        self.assertTrue(callable(server.get_course_contents))
        self.assertTrue(callable(server.get_materials))
        self.assertTrue(callable(server.get_assignments))
        self.assertTrue(callable(server.get_assignment_detail))
        self.assertTrue(callable(server.download_file))
        self.assertTrue(callable(server.get_deadlines))
        self.assertTrue(callable(server.get_grades))
        self.assertTrue(callable(server.set_session))
        self.assertTrue(callable(server.session_status))

    def test_fastmcp_tools_registration(self):
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        registered_tools = [tool.name for tool in tools]
        expected_tools = [
            "set_session",
            "session_status",
            "get_profile",
            "list_courses",
            "get_course_contents",
            "get_materials",
            "get_assignments",
            "get_assignment_detail",
            "download_file",
            "get_deadlines",
            "get_grades",
        ]
        for tool in expected_tools:
            self.assertIn(tool, registered_tools)


if __name__ == "__main__":
    unittest.main()
