import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/package_wave64_openslr31_speaker_identity_evidence.py"
)
SPEC = importlib.util.spec_from_file_location(
    "package_wave64_openslr31_speaker_identity_evidence", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def valid_manifest():
    return {
        "status": "PASS_DISJOINT_SPEAKER_THRESHOLD_AND_CHAIN_IDENTITY_PRODUCTION_AUTHORITY_BLOCKED",
        "dataset": {
            "speaker_count": 26,
            "utterance_count": 1089,
            "clips_per_speaker": 6,
            "speaker_overlap_count": 0,
            "calibration_speaker_ids": [str(index) for index in range(13)],
            "validation_speaker_ids": [str(index) for index in range(13, 26)],
        },
        "pair_scoring": {
            "calibration": {"positive_count": 195, "different_speaker_count": 2808},
            "validation": {"positive_count": 195, "different_speaker_count": 2808},
        },
        "threshold_validation": {
            "threshold": 0.33445611596107483,
            "calibration": {
                "true_positive_rate": 1.0,
                "false_positive_rate": 0.02207977207977208,
            },
            "validation": {
                "true_positive_rate": 0.9948717948717949,
                "false_positive_rate": 0.02564102564102564,
            },
            "speaker_disjoint_validation_pass": True,
        },
        "chain_specific_evaluation": {
            "speaker_similarity": 0.9932656288146973,
            "chain_specific_identity_preservation_pass": True,
        },
        "acceptance": {
            "official_archive_hash_verified": True,
            "official_resource_license_declaration_verified": True,
            "numeric_speaker_labels_verified": True,
            "speaker_disjoint_validation_pass": True,
            "threshold_deployment_allowed_for_chain_specific_evaluation": True,
            "chain_specific_identity_preservation_pass": True,
            "universal_biometric_identity_claim_allowed": False,
            "parler_candidate_reference_identity_claim_allowed": False,
            "emotion_or_style_claim_allowed": False,
            "independent_perceptual_playback_review_pass": False,
            "production_review_authority_allowed": False,
            "authority_registry_mutation_allowed": False,
            "row_completion_allowed": False,
        },
        "row_complete": False,
    }


class OpenSLR31SpeakerEvidencePackagingTests(unittest.TestCase):
    def test_verify_manifest_accepts_exact_fail_closed_result(self):
        MODULE.verify_manifest(valid_manifest())

    def test_verify_manifest_rejects_validation_fpr_drift(self):
        payload = valid_manifest()
        payload["threshold_validation"]["validation"]["false_positive_rate"] = 0.11
        with self.assertRaisesRegex(ValueError, "threshold metrics drift"):
            MODULE.verify_manifest(payload)

    def test_verify_manifest_rejects_production_authority(self):
        payload = valid_manifest()
        payload["acceptance"]["production_review_authority_allowed"] = True
        with self.assertRaisesRegex(ValueError, "must remain false"):
            MODULE.verify_manifest(payload)

    def test_verify_manifest_rejects_row_completion(self):
        payload = valid_manifest()
        payload["row_complete"] = True
        with self.assertRaisesRegex(ValueError, "cannot complete a row"):
            MODULE.verify_manifest(payload)


if __name__ == "__main__":
    unittest.main()
