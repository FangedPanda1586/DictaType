from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "dictatype" / "ui.py").read_text(encoding="utf-8")
CLASSROOM = (ROOT / "dictatype" / "classroom.py").read_text(encoding="utf-8")


class ExamNetworkOpenJoinTests(unittest.TestCase):
    def test_exam_defaults_to_open_name_and_class_join(self):
        self.assertIn(
            'Exam mode opens a room on the local network. Students join in a browser with the room address and code, then enter their own name and class.',
            UI,
        )
        exam_block = UI.split('if is_exam:', 1)[1].split('else:', 1)[0]
        self.assertIn('self.allow_new_profiles_var.set(True)', exam_block)
        self.assertIn('Open join: students enter their own name and class (recommended)', UI)

    def test_http_server_listens_on_all_local_interfaces(self):
        self.assertIn('NETWORK_BIND_HOST = "0.0.0.0"', CLASSROOM)
        self.assertIn('ThreadingHTTPServer((NETWORK_BIND_HOST, candidate), Handler)', CLASSROOM)
        self.assertIn('def network_urls(self) -> list[str]:', CLASSROOM)

    def test_exam_requires_name_and_class_for_identifiable_results(self):
        self.assertIn('Student name is required.', CLASSROOM)
        self.assertGreaterEqual(
            CLASSROOM.count('server.session_type == "exam" and not class_name'),
            2,
        )
        self.assertIn('Class is required for an exam. Enter your class and try again.', CLASSROOM)

    def test_student_join_page_collects_name_class_and_code(self):
        self.assertIn('id="name"', CLASSROOM)
        self.assertIn('id="className"', CLASSROOM)
        self.assertIn('id="code"', CLASSROOM)
        self.assertIn('Enter your name and class exactly as they should appear', CLASSROOM)

    def test_teacher_room_details_make_lan_status_visible(self):
        self.assertIn('LAN OPEN', UI)
        self.assertIn('Network access: OPEN on all local adapters', UI)
        self.assertIn('If Windows Firewall asks, allow DictaType on Private networks.', UI)


if __name__ == "__main__":
    unittest.main()
