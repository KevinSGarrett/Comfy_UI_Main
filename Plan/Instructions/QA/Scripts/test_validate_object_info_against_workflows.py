import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION"
    / "scripts"
    / "validate_object_info_against_workflows.py"
)
SPEC = importlib.util.spec_from_file_location("validate_object_info", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WorkflowNodeTypesTests(unittest.TestCase):
    def write_json(self, payload):
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with handle:
            json.dump(payload, handle)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        return Path(handle.name)

    def test_extracts_ui_workflow_types(self):
        path = self.write_json({"nodes": [{"type": "LoadImage"}, {"type": "KSampler"}]})
        node_types, workflow_format = MODULE.workflow_node_types(path)
        self.assertEqual(node_types, {"LoadImage", "KSampler"})
        self.assertEqual(workflow_format, "ui_workflow")

    def test_extracts_api_workflow_types(self):
        path = self.write_json(
            {
                "1": {"class_type": "UNETLoader", "inputs": {}},
                "2": {"class_type": "Wan22ImageToVideoLatent", "inputs": {}},
            }
        )
        node_types, workflow_format = MODULE.workflow_node_types(path)
        self.assertEqual(node_types, {"UNETLoader", "Wan22ImageToVideoLatent"})
        self.assertEqual(workflow_format, "api_workflow")

    def test_extracts_prompt_request_types(self):
        path = self.write_json({"prompt": {"1": {"class_type": "SaveVideo", "inputs": {}}}})
        node_types, workflow_format = MODULE.workflow_node_types(path)
        self.assertEqual(node_types, {"SaveVideo"})
        self.assertEqual(workflow_format, "prompt_request")

    def test_rejects_unrecognized_or_empty_workflow(self):
        path = self.write_json({"nodes": []})
        node_types, workflow_format = MODULE.workflow_node_types(path)
        self.assertEqual(node_types, set())
        self.assertEqual(workflow_format, "ui_workflow")


if __name__ == "__main__":
    unittest.main()
