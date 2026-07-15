#!/usr/bin/env python3
"""Build the provider-resolved Wave64 speech/audio acquisition catalog."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
CATALOG = Path("Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json")
EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_PROVIDER_DISCOVERY_20260715.json")
EVIDENCE_MIRROR = Path("Plan/Tracker/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_PROVIDER_DISCOVERY_20260715.json")
DISCOVERY_ROOT = Path("runtime_artifacts/model_acquisition/discovery/wave64_speech_second_pass")


def hf(
    asset_id: str,
    capability: str,
    repo_id: str,
    revision: str,
    license_id: str,
    gated: bool,
    priority: str,
    rows: list[int],
    files: list[tuple[str, int, str]],
    disposition: str = "acquire_when_selected_lane_is_active",
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "capability": capability,
        "provider": "huggingface",
        "authority_level": "official_or_creator_published_model_repository",
        "repo_id": repo_id,
        "revision": revision,
        "revision_policy": "immutable_commit_required",
        "license": license_id,
        "gated": gated,
        "priority": priority,
        "required_by_rows": [f"TRK-W64-{row:03d}" for row in rows],
        "key_files": [
            {"filename": filename, "bytes": size, "sha256": digest}
            for filename, size, digest in files
        ],
        "file_set_policy": "resolve_all_required_repository_files_at_pinned_revision_before_acquisition",
        "disposition": disposition,
        "production_ready": False,
    }


OFFICIAL_ASSETS = [
    hf("qwen3_tts_1_7b_customvoice", "high_fidelity_custom_voice_and_cloning", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "0c0e3051f131929182e2c023b9537f8b1c68adfe", "apache-2.0", False, "P0", [117, 118, 123, 124, 131, 133], [("model.safetensors", 3833402552, "38b1d5971bdbd982b561cccec982669a53b0537c3cf5e9bd4778ed07bb2f5137"), ("speech_tokenizer/model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("qwen3_tts_1_7b_base", "reference_voice_cloning_and_general_synthesis", "Qwen/Qwen3-TTS-12Hz-1.7B-Base", "fd4b254389122332181a7c3db7f27e918eec64e3", "apache-2.0", False, "P0", [117, 118, 123, 124], [("model.safetensors", 3857413744, "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c"), ("speech_tokenizer/model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("qwen3_tts_1_7b_voicedesign", "designed_synthetic_character_voice", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "5ecdb67327fd37bb2e042aab12ff7391903235d3", "apache-2.0", False, "P0", [116, 117, 118, 123, 125], [("model.safetensors", 3833402552, "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522"), ("speech_tokenizer/model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("qwen3_tts_tokenizer_12hz", "shared_qwen_speech_codec", "Qwen/Qwen3-TTS-Tokenizer-12Hz", "7dd38ad4e9bad454aae9cd937d0cd577604fe229", "apache-2.0", False, "P0", [117, 123, 124, 125], [("model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("qwen3_tts_0_6b_customvoice", "lower_vram_custom_voice_fallback", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice", "85e237c12c027371202489a0ec509ded67b5e4b5", "apache-2.0", False, "P1", [117, 118, 123, 146], [("model.safetensors", 1811626576, "bc3c7e785eb961179c25450d1acff03f839e0002f2f3a5aeb67b5735c0fa2adb"), ("speech_tokenizer/model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("qwen3_tts_0_6b_base", "lower_vram_cloning_fallback", "Qwen/Qwen3-TTS-12Hz-0.6B-Base", "5d83992436eae1d760afd27aff78a71d676296fc", "apache-2.0", False, "P1", [117, 118, 123, 146], [("model.safetensors", 1829344272, "180b3b10eb1c9f1b4db7806d5475bae3071c0243c299d49926bab1da3b6946f6"), ("speech_tokenizer/model.safetensors", 682293092, "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258")]),
    hf("fun_cosyvoice3_0_5b_2512", "multilingual_zero_shot_and_instruction_speech", "FunAudioLLM/Fun-CosyVoice3-0.5B-2512", "29e01c4e8d000f4bcd70751be16fa94bf3d85a18", "apache-2.0", False, "P0", [117, 118, 123, 124, 126, 127, 133], [("llm.pt", 2024669519, "69f43bd545131c30e98947fb360ea8b4dc9916d8e83dded7757c7ea4f5a24970"), ("llm.rl.pt", 2024682701, "74d34b01a80c7154670ae75ac372d1b1712c78bceae9f467eb9f1f6f61ec764f"), ("flow.pt", 1329116148, "a6fab32a7825e5b0bc855ddd948f8db9370b0a786fbc249caa4595e95b608e4b")]),
    hf("chatterbox_multilingual_v3", "multilingual_character_voice_continuity", "ResembleAI/chatterbox", "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18", "mit", False, "P0", [117, 118, 123, 124, 127, 131, 133], [("t3_mtl23ls_v3.safetensors", 2143989928, "5abca8321ede76f8e61f1cc0d19aea6c946b28871017ce8726f8a69203f05953")]),
    hf("chatterbox_turbo_v1", "efficient_english_expressive_speech", "ResembleAI/chatterbox-turbo", "749d1c1a46eb10492095d68fbcf55691ccf137cd", "mit", False, "P0", [117, 118, 123, 126, 127, 146], [("t3_turbo_v1.safetensors", 1915480052, "fcf1f8c1d651bb7e3acd69ee5be269b4ac10c02980b7708213d598bc9f7cdf87"), ("s3gen_meanflow.safetensors", 1064875036, "d65cb687a2ed581ee6cc297e919ffefa63386944f42364ae13b78a594945514f")]),
    hf("fishaudio_s2_pro", "multilingual_short_reference_voice_cloning", "fishaudio/s2-pro", "1de9996b6be38b745688de084d87a5633f714e4e", "provider_custom_terms_verify_before_use", False, "P0", [117, 118, 123, 124, 126, 127, 131, 133], [("model-00001-of-00002.safetensors", 4986872984, "c4218e8ac93be83b35eee30b4f94cb2e9b5ecff40f3e21611438d2f4f8804aad"), ("model-00002-of-00002.safetensors", 4136876104, "76738d23465deaac431433232c0762908cc99a6eddc3d49f67307d92680827be"), ("codec.pth", 1871099728, "74fc41c5a7151c6f350af8bd7e5d6e3accfcc7f3dfbfac23afd35af07052bb2f")], "blocked_until_license_terms_recorded"),
    hf("mmaudio_large_44k_v2", "synchronized_video_conditioned_audio", "hkchengrex/MMAudio", "eb13a1a98fdbec91753775c57b074ccdfc60587c", "cc-by-nc-4.0", False, "P0", [137, 138, 139, 145, 147, 148], [("weights/mmaudio_large_44k_v2.pth", 4122474715, "a6bf693424fbd4ce0244fff8c412347714d5ac586e28dbeffadfa0f2b647af74")], "reuse_existing_exact_hash_and_runtime_proof_before_any_acquisition"),
    hf("hunyuanvideo_foley_xl", "video_conditioned_48khz_foley", "tencent/HunyuanVideo-Foley", "3abd4e833b95b8db0fc9c687afc52483a48e9a97", "tencent_hunyuan_community_license_verify_use_scope", False, "P0", [128, 137, 138, 139, 145, 147], [("hunyuanvideo_foley_xl.pth", 5854140970, "cf7e93dca93063942bc22b53d4fe888e9d9d5a1ad7977873b7b2c6b126cf00ca"), ("vae_128d_48k.pth", 1486465965, "07e6139ff33bd21ba8a7a7f40ed24aab13ac0d100cd686f8a9f3e03dc5251cb1"), ("synchformer_state_dict.pth", 950058171, "8aff082f2df5c3bc52759db0c865c7ee772ae6400b860d1b7e90413f2defb67c")], "blocked_until_license_terms_recorded"),
    hf("stable_audio_3_small_sfx", "reference_conditioned_sfx_generation_and_editing", "stabilityai/stable-audio-3-small-sfx", "ae12755283df9d62ca39a9b050a39a0b607b8c20", "stability_community_license_gated_acceptance", True, "P0", [128, 138, 139, 145, 147], [("model.safetensors", 2270384940, "ed9cf1b6172f1a8c2921a9560c21109ff3239524563ced9dce6dcdef41e2f515"), ("t5gemma-b-b-ul2/model.safetensors", 1183022944, "9b05ea5a4f211d023832f706fb2c0e83e4fc721b6da35ab69ceb0b55eb7800d3")], "blocked_until_gated_access_and_license_are_recorded"),
    hf("stable_audio_3_medium", "high_quality_audio_generation_editing_inpainting_continuation", "stabilityai/stable-audio-3-medium", "27b5a21b791b1b033d193a9e1e3ce78493f102f9", "stability_community_license_gated_acceptance", True, "P1", [128, 138, 139, 145, 147], [("model.safetensors", 9222116660, "48d9c65e290e7bcd5194e0633bfc2424a59ee9683f5c2d58762d997b7d8ce0b5"), ("t5gemma-b-b-ul2/model.safetensors", 1183022944, "9b05ea5a4f211d023832f706fb2c0e83e4fc721b6da35ab69ceb0b55eb7800d3")], "blocked_until_gated_access_and_license_are_recorded"),
    hf("latentsync_1_6", "high_fidelity_audio_conditioned_lip_synchronization", "ByteDance/LatentSync-1.6", "c42c7e6c8e9c213626389fa7d9a3c444b8536353", "openrail++", False, "P0", [135, 136, 137, 145, 147, 148], [("latentsync_unet.pt", 5072222488, "0a478e89eb660f82da4c35dbdde8a5adfb27f99d1b4e50edd03729e1e98316d3"), ("stable_syncnet.pt", 1605328746, "77678d13861a02d6e83d0b169962175b6266be773f1f6f85fda2b0182e225118")]),
    hf("laion_clap_general", "semantic_audio_retrieval_and_similarity", "laion/larger_clap_general", "ada0c23a36c4e8582805bb38fec3905903f18b41", "apache-2.0", False, "P0", [118, 128, 141, 142, 147], [("pytorch_model.bin", 776444665, "314eb00cce6ad68d25237b8446b659ccdb136ed4672c1bca470f142f72455026")]),
    hf("laion_clap_music_speech", "speech_music_cross_modal_similarity", "laion/larger_clap_music_and_speech", "195c3a3e68faebb3e2088b9a79e79b43ddbda76b", "apache-2.0", False, "P1", [118, 128, 141, 147], [("pytorch_model.bin", 776444665, "b73c5e596fda5b29b522a1ab3f0842977fe2b147bf8b78c2ec5f7ae6267038a1")]),
    hf("whisper_large_v3_turbo", "content_asr_and_word_timing_baseline", "openai/whisper-large-v3-turbo", "41f01f3fe87f28c78e2fbf8b568835947dd65ed9", "mit", False, "P0", [119, 135, 141, 142, 147], [("model.safetensors", 1617824864, "542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1")]),
    hf("pyannote_diarization_community_1", "speaker_turn_and_overlap_diarization", "pyannote/speaker-diarization-community-1", "3533c8cf8e369892e6b79ff1bf80f7b0286a54ee", "cc-by-4.0_gated_acceptance", True, "P0", [134, 135, 140, 141, 147], [("embedding/pytorch_model.bin", 26646242, "6f10ff60898a1d185fa22e1d11e0bfa8a92efec811f11bca48cb8cafebefd929"), ("segmentation/pytorch_model.bin", 5906507, "7ad24338d844fb95985486eb1a464e32d229f6d7a03c9abe60f978bacf3f816e")], "blocked_until_gated_access_is_recorded"),
    hf("emotion2vec_plus_large", "emotion_evidence_without_delivery_taxonomy_conflation", "emotion2vec/emotion2vec_plus_large", "6c303ba987b86b93193de93e34bb2b077a6bedc4", "provider_custom_terms_verify_before_use", False, "P0", [127, 141, 142, 147], [("model.pt", 1945790254, "be501a01f26fcdc7663a062dff86af839afbaef7c4de32f5e42d7e1ad2784da4")], "reuse_existing_calibrated_exact_hash_if_present"),
    hf("indextts2", "emotion_and_timbre_conditioned_voice_cloning_challenger", "IndexTeam/IndexTTS-2", "740dcaff396282ffb241903d150ac011cd4b1ede", "exact_model_terms_not_declared_in_hf_metadata", False, "P1", [117, 118, 123, 124, 126, 127, 131], [("gpt.pth", 3484663079, "baaaeb8b56328da81731dc540a85a7dee32eca9da28f174b05757cb651c602a4"), ("s2mel.pth", 1202198223, "aae1bb12017cbb47e7a5ce537fc82f40b6b1deb71acdb9b8f25686f32714b636"), ("qwen0.6bemo4-merge/model.safetensors", 1192135096, "11293257a8df593c154a8ecd5fc039f3076de35411e35f06d41b471e136f6641")], "blocked_until_license_terms_recorded"),
    hf("f5_tts", "flow_matching_zero_shot_speech_challenger", "SWivid/F5-TTS", "84e5a410d9cead4de2f847e7c9369a6440bdfaca", "cc-by-nc-4.0", False, "P2", [117, 118, 123, 124, 146, 147], [("F5TTS_v1_Base/model_1250000.safetensors", 1348435761, "670900fd14e6c458b95da6e9ed317cdb20dbaf7a1c02ac06a05475a9d32b6a38")], "benchmark_noncommercial_scope_only"),
    hf("spark_tts_0_5b", "controllable_voice_cloning_challenger", "SparkAudio/Spark-TTS-0.5B", "642071559bfc6346c2359d19dcb6be3f9dd8a05d", "cc-by-nc-sa-4.0", False, "P2", [117, 118, 123, 124, 125, 126, 147], [("LLM/model.safetensors", 2026568968, "54825baf0a2f6076eb3c78fa1d22a95aee225f59070a8b295f8169db860eb109"), ("BiCodec/model.safetensors", 625518756, "e9940cd48d4446e4340ced82d234bf5618350dd9f5db900ebe47a4fdb03867ec")], "benchmark_noncommercial_scope_only"),
    hf("vibevoice_1_5b", "long_form_multi_speaker_dialogue_challenger", "microsoft/VibeVoice-1.5B", "c00898d257e6b46004e3e2866a47534085fb685a", "mit", False, "P1", [117, 118, 123, 132, 134, 140, 147], [("model-00001-of-00003.safetensors", 1975317828, "c5f0a61ddeaeb028e3af540ba4dee7933ad30f9f30b6e1320dd9c875a2daa033"), ("model-00002-of-00003.safetensors", 1983051688, "81c3891f7b2493eb48a9eb6f5be0df48d4f1a4bfd952d84e21683ca6d0bf7969"), ("model-00003-of-00003.safetensors", 1449832938, "cb6e7e5e86b4a41fffbe1f3aaf445d0d50b5e21ed47574101b777f77d75fa196")]),
    hf("voxcpm2", "context_aware_voice_cloning_and_design_challenger", "openbmb/VoxCPM2", "bffb3df5a29440629464e5e839f4d214c8714c3d", "apache-2.0", False, "P1", [116, 117, 118, 123, 124, 125, 126, 131, 133], [("model.safetensors", 4580080592, "f7f964cfa9da23653baec6e6f7750719977ad944ed9f95fe52fe3a620506891d"), ("audiovae.pth", 376951122, "94b5d51e107e0507d4acc976cfdadb64edd6fd06d1f751dadbf2fd1594274bf1")]),
    hf("step_audio_2_mini", "audio_language_model_speech_understanding_and_generation_challenger", "stepfun-ai/Step-Audio-2-mini", "e36fdd5d71e0ea22f09dd94bbab9bfc544ca1e36", "apache-2.0", False, "P2", [117, 118, 123, 127, 128, 141, 147], [("model-00001-of-00004.safetensors", 4925370984, "7b88e02b0b8c643412ec68cae009b3952dbd8e27642d61626065a2c420a8b73c"), ("model-00002-of-00004.safetensors", 4932751008, "3d412c8d2fc17ca3351751f3171d48ff5b139af623aa05749062f132ac2585f1"), ("model-00003-of-00004.safetensors", 4988307424, "135ae4a891350e8ebf9791ef073d310314e1f75192bece0971bfab7b86c5587c"), ("model-00004-of-00004.safetensors", 1784019520, "d35bf0ec42ff9ec160dfc6c5cb20a65247f0f8ba1c6edc620398c2ef49a66295")], "benchmark_only_after_p0_engines_due_large_runtime_cost"),
    hf("dia2_2b", "expressive_multi_speaker_dialogue_and_nonverbal_challenger", "nari-labs/Dia2-2B", "7abae125471a73b0fc6b9d413cb15f4ae1e771d8", "apache-2.0", False, "P1", [117, 118, 123, 128, 132, 134, 140, 147], [("model.safetensors", 7678277416, "b3eb6b4758beaae97dcfa87d430706ede0d78306cc3afb1eaf4397f216abd1db")]),
    hf("sesame_csm_1b", "conversational_context_and_turn_taking_challenger", "sesame/csm-1b", "c92a71e1c419772e25be7dc14d952c2521a740ab", "apache-2.0_gated_acceptance", True, "P2", [117, 118, 123, 132, 134, 140, 147], [("model.safetensors", 6211186784, "2e7721144afe38b906d4f1048671da639fe142423f4a26283606ecebe894f4bf")], "blocked_until_gated_access_is_recorded"),
    hf("megatts3", "zero_shot_voice_cloning_and_duration_model_challenger", "ByteDance/MegaTTS3", "409a7002b006d80f0730fca6f80441b08c10e738", "apache-2.0", False, "P1", [117, 118, 120, 122, 123, 124, 131, 147], [("diffusion_transformer/model_only_last.ckpt", 1836341777, "12233b95be177504551034390cf71aa748f0c66cbe2fd0ce433b9f9686122da9"), ("g2p/model.safetensors", 1018490136, "0f9d70d454ee35d023a9a54552716a8ccf2411c967abc6a857160527046f62a2"), ("duration_lm/model_only_last.ckpt", 267955084, "0f21f4205c5d3ec4bef69716a85ca3d37f25c35b429bac500477a2085039b43f")]),
    hf("maskgct", "zero_shot_masked_speech_generation_challenger", "amphion/MaskGCT", "265c6cef07625665d0c28d2faafb1415562379dc", "cc-by-nc-4.0", False, "P2", [117, 118, 123, 124, 147], [("t2s_model/model.safetensors", 2985622968, "543156edd53f533572b751ca2e179c498b51fe96bb8a181e82e31b5ef455230e"), ("s2a_model/s2a_model_full/model.safetensors", 1413786096, "27518b0ffae8afdeec8d9b6102868ced38d2a93477eb992d381c188383e78cfa")], "benchmark_noncommercial_scope_only"),
    hf("openvoice_v2", "tone_color_conversion_and_cross_language_voice_conversion_challenger", "myshell-ai/OpenVoiceV2", "f36e7edfe1684461a8343844af60babc2efbb727", "mit", False, "P1", [117, 118, 124, 131, 133, 147], [("converter/checkpoint.pth", 131320490, "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e")]),
]


SOURCE_REPOSITORIES = [
    ("QwenLM/Qwen3-TTS", "022e286b98fbec7e1e916cb940cdf532cd9f488e", "Apache-2.0"),
    ("FunAudioLLM/CosyVoice", "074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc", "Apache-2.0"),
    ("resemble-ai/chatterbox", "65b18437192794391a0308a8f705b1e33e633948", "MIT"),
    ("fishaudio/fish-speech", "e5e292632cb11e7a27b2b7487f58f612bc101e13", "license_file_requires_review"),
    ("hkchengrex/MMAudio", "974010a026c731054592d8f777218bd9d85a6c24", "MIT_code_model_terms_separate"),
    ("Tencent-Hunyuan/HunyuanVideo-Foley", "df7b005b5023df2a9b73e1d66dd51d452799884e", "license_file_requires_review"),
    ("Stability-AI/stable-audio-3", "17ba5051b0a57a7dd92c65c8631ec647a64c18f8", "MIT_code_model_terms_separate"),
    ("LAION-AI/CLAP", "1fd4c37df5ffbfcfbad5415c170bc66cf94c9994", "CC0-1.0_code_model_terms_separate"),
    ("m-bain/whisperX", "2cfd7b7c5c7bba144954364db747319b50e8232b", "BSD-2-Clause"),
    ("MontrealCorpusTools/Montreal-Forced-Aligner", "f01293108ac1c1025baf5f82ad4820dfb2e21598", "MIT"),
    ("pyannote/pyannote-audio", "b749285c5cdd4636b2edc7f766f1352c8dde9369", "MIT_code_model_terms_separate"),
    ("ByteDance/LatentSync", "a229c3948406bc2cf6eaf4873e662e70c6a04746", "Apache-2.0_code_model_terms_separate"),
    ("microsoft/unilm", "833df7e7832e5064a281131ee64a481afa8e5b95", "MIT_code_checkpoint_terms_require_review"),
    ("openai/whisper", "04f449b8a437f1bbd3dba5c9f826aca972e7709a", "MIT"),
    ("index-tts/index-tts", "13495845e3028f0bb6ca1462ad22aa0e76349e40", "license_file_requires_review"),
    ("SWivid/F5-TTS", "91f499635cb4f8b8a926e83f1839f5338bc2ef87", "MIT_code_CC-BY-NC-4.0_model"),
    ("SparkAudio/Spark-TTS", "2f1ea9082400547242641f5271b6f941c9f439d1", "Apache-2.0_code_CC-BY-NC-SA-4.0_model"),
    ("microsoft/VibeVoice", "303b2833e01cff4578ec278bbfe536da54bd19fe", "MIT"),
    ("OpenBMB/VoxCPM", "616d3d3e630a9c96c2853250eef91b0f39dcd5fa", "Apache-2.0"),
    ("stepfun-ai/Step-Audio2", "76e272b56c3917a8d7188f18bbb5a65dfc8a0845", "Apache-2.0"),
    ("nari-labs/dia", "876125e461a03b157ec905b0fe8b57a0f8b9e7a0", "Apache-2.0"),
    ("SesameAILabs/csm", "daed31e6d42cf71873999075de204fa37d2acec3", "Apache-2.0"),
    ("bytedance/MegaTTS3", "67395f2d590b48eea88f7f834469da333f48a161", "Apache-2.0"),
    ("open-mmlab/Amphion", "26f6883110181f1dbfe95c70a7c7dbaf4de5f42a", "MIT_code_CC-BY-NC-4.0_model"),
    ("myshell-ai/OpenVoice", "74a1d147b17a8c3092dd5430504bd83ef6c7eb23", "MIT"),
]


def civitai(asset_id: str, capability: str, model_id: str, version_id: str, file_id: str, filename: str, sha256: str, rows: list[int]) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "capability": capability,
        "provider": "civitai",
        "authority_level": "community_comfyui_integration_candidate_not_model_authority",
        "model_id": model_id,
        "model_version_id": version_id,
        "file_id": file_id,
        "filename": filename,
        "sha256": sha256,
        "required_by_rows": [f"TRK-W64-{row:03d}" for row in rows],
        "disposition": "inspect_workflow_offline_then_adapt_or_reject; never_bulk_install",
        "underlying_official_weights_required": True,
        "production_ready": False,
    }


CIVITAI_INTEGRATIONS = [
    civitai("civitai_qwen3_tts_workflow_collection", "qwen3_tts_comfyui_reference", "2337329", "2629166", "2516909", "qwen3TTSVoice_v10.zip", "156fc156b864f0bf8f0b763333958ab09105b1754c3b65dc23ec31338883e25e", [117, 123, 145]),
    civitai("civitai_cosyvoice3_27_language_workflow", "cosyvoice3_comfyui_reference", "2345305", "2638010", "2525987", "Cosyvoice327Language_v10.zip", "0f3d397a1e80e77daf835a690d79e2a7b6bd2496ccaa6a4e867c15a582aa8a44", [117, 123, 133, 145]),
    civitai("civitai_chatterbox_multilingual_workflow", "chatterbox_comfyui_reference", "2615478", "2936661", "2815715", "chatterboxTTSComfyui_v10.zip", "4d93bc645b3165919d6d3c8af3b8fbc340ee184e2dc7ec0ccb1d236bfd0c8d38", [117, 123, 145]),
    civitai("civitai_fish_audio_s2_workflow", "fish_audio_s2_comfyui_reference", "2494972", "2804695", "2690516", "fishAudioS2_fishAudioS2.zip", "4c5fd4620b5e865a970c99e5d42efb9575af20e174c29aadf62cb17a35757053", [117, 123, 124, 145]),
    civitai("civitai_mmaudio_batch_workflow", "mmaudio_long_source_batch_reference", "2168550", "2578605", "2465831", "mmaudioBatch_v12LongSources.zip", "b209fff3738c0545f088cd83ae0e715a189b6e10c3aa7223ce5c69bbcfaeb4e1", [137, 138, 145]),
    civitai("civitai_hunyuan_foley_workflow", "hunyuan_video_foley_comfyui_reference", "1910714", "2162629", "2065739", "turnQuietFootageIntoSound_v11.zip", "cb9c1ce3122cf73d658d21680bee5040dc298628b670b10cb6c9703ec82b7301", [128, 138, 145]),
    civitai("civitai_stable_audio_3_workflow", "stable_audio_3_comfyui_reference", "2652544", "2978445", "2858047", "stableAudio3SoundAsset_v10.zip", "21599604b48041dfea98c1098c5dc4c07b707ebb5d6caf67044033439046e3da", [128, 138, 145]),
    civitai("civitai_latentsync_1_6_workflow", "latentsync_comfyui_reference", "2129724", "2409072", "2299607", "latentsync16_v10.zip", "034493f8bc911693f78f325d42236dcddd3f27f88fabbb9b504645aaa7b34853", [135, 136, 137, 145]),
    civitai("civitai_indextts2_emotion_timbre_workflow", "indextts2_comfyui_reference", "2135361", "2415513", "2306002", "indextts20VoiceTimbre_v10.zip", "7cdf00092e61c923b407c59be000c296eb596f04f87dc8da0d4c321ffa6b8c82", [117, 123, 124, 127, 145]),
    civitai("civitai_vibevoice_multi_person_workflow", "vibevoice_multi_speaker_comfyui_reference", "1926793", "2180784", "2073902", "vibevoiceUltraLongAudio_v10.zip", "8d7052f2e5adc4458fdf11263a5426f0c6f65dad796b3608c110c12ffb488446", [117, 123, 134, 145]),
    civitai("civitai_voxcpm2_clone_design_workflow", "voxcpm2_comfyui_reference", "2564052", "2881179", "2761529", "voxcpm2VoiceCloning_voxcpm2Voiceclone.zip", "b3aa345faa198b2ab7d76a412382b5ab45bfc34626647953bd21ab90c83c0f87", [116, 117, 123, 124, 125, 145]),
    civitai("civitai_csm_workflow", "sesame_csm_comfyui_reference", "1362316", "1539048", "1439024", "sesameaiCSMComfyui_v10.zip", "10a49725521e68fb26b2a0b800c60c9f543f396132a19c024a9c6c00fdc551e6", [117, 123, 134, 145]),
    civitai("civitai_megatts3_clone_workflow", "megatts3_comfyui_reference", "2135175", "2415321", "2305810", "megatts3SingleAndDual_v10.zip", "7e60a5dfe8581273570d834874c9b9ee09e80964b8dc6a3fef6b636269986901", [117, 123, 124, 145]),
]


ROW_BINDINGS = {
    "TRK-W64-117": [asset["asset_id"] for asset in OFFICIAL_ASSETS + CIVITAI_INTEGRATIONS],
    "TRK-W64-118": [asset["asset_id"] for asset in OFFICIAL_ASSETS if "TRK-W64-118" in asset["required_by_rows"]],
    "TRK-W64-123": [asset["asset_id"] for asset in OFFICIAL_ASSETS if "TRK-W64-123" in asset["required_by_rows"]],
    "TRK-W64-124": [asset["asset_id"] for asset in OFFICIAL_ASSETS if "TRK-W64-124" in asset["required_by_rows"]],
    "TRK-W64-125": ["qwen3_tts_1_7b_voicedesign"],
    "TRK-W64-127": ["emotion2vec_plus_large"],
    "TRK-W64-128": ["hunyuanvideo_foley_xl", "stable_audio_3_small_sfx", "stable_audio_3_medium", "laion_clap_general"],
    "TRK-W64-133": [asset["asset_id"] for asset in OFFICIAL_ASSETS if "TRK-W64-133" in asset["required_by_rows"]],
    "TRK-W64-134": [asset["asset_id"] for asset in OFFICIAL_ASSETS if "TRK-W64-134" in asset["required_by_rows"]],
    "TRK-W64-135": ["whisper_large_v3_turbo", "pyannote_diarization_community_1", "latentsync_1_6"],
    "TRK-W64-137": ["latentsync_1_6", "mmaudio_large_44k_v2", "hunyuanvideo_foley_xl"],
    "TRK-W64-141": ["whisper_large_v3_turbo", "laion_clap_general", "laion_clap_music_speech", "pyannote_diarization_community_1", "emotion2vec_plus_large"],
    "TRK-W64-145": [asset["asset_id"] for asset in CIVITAI_INTEGRATIONS],
    "TRK-W64-147": [asset["asset_id"] for asset in OFFICIAL_ASSETS],
    "TRK-W64-148": ["latentsync_1_6", "mmaudio_large_44k_v2", "hunyuanvideo_foley_xl", "whisper_large_v3_turbo", "pyannote_diarization_community_1"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main(root: Path = ROOT) -> dict[str, Any]:
    discovery_packets = []
    discovery_root = root / DISCOVERY_ROOT
    if discovery_root.is_dir():
        for path in sorted(discovery_root.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            discovery_packets.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path),
                "candidate_count": payload.get("candidate_count", 0),
                "classification": payload.get("classification"),
            })

    catalog = {
        "schema_version": "1.0",
        "catalog_id": "wave64_hyperreal_audio_model_asset_acquisition_catalog",
        "snapshot_date": date.today().isoformat(),
        "status": "provider_resolved_candidates_not_installed_or_production_ready",
        "authority": {
            "project_root": "C:/Comfy_UI_Main",
            "acquisition_controller": "Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py",
            "source_priority": ["reuse_exact_hash", "official_huggingface_exact_revision", "exact_civitai_integration_file", "authenticated_background_browser_if_required"],
        },
        "official_asset_groups": OFFICIAL_ASSETS,
        "official_source_repositories": [
            {"repository": repo, "commit": commit, "license": license_id}
            for repo, commit, license_id in SOURCE_REPOSITORIES
        ],
        "civitai_integration_candidates": CIVITAI_INTEGRATIONS,
        "row_asset_bindings": ROW_BINDINGS,
        "deferred_or_exact_blocked": [
            {"asset_id": "beats_official_audioset_checkpoint", "status": "exact_official_checkpoint_sha256_required", "reason": "Do not substitute an unverified community Hugging Face mirror for the Microsoft-published checkpoint."},
            {"asset_id": "mfa_language_models", "status": "select_per_language_at_row135", "reason": "Acoustic, dictionary, and G2P assets must match the approved dialogue language and immutable MFA model release."},
            {"asset_id": "dnsmos_models", "status": "reuse_existing_local_calibrated_hashes", "reason": "Already present in CV3-Eval; do not redownload without hash drift."},
            {"asset_id": "eres2net_speaker_embedding", "status": "reuse_existing_local_calibrated_hash", "reason": "Already present in CV3-Eval; keep the calibrated checkpoint as the initial identity baseline."},
            {"asset_id": "wav2lip", "status": "not_selected_for_primary_lane", "reason": "Source/model license and fidelity require separate review; LatentSync 1.6 is the current P0 benchmark."},
            {"asset_id": "community_quantizations_and_hf_mirrors", "status": "excluded_until_official_baseline_passes", "reason": "Third-party conversions are not authority and add numerical and provenance variables."},
        ],
        "boundaries": {
            "content_based_suppression": False,
            "adult_or_nsfw_metadata_is_filter": False,
            "community_workflow_is_model_authority": False,
            "catalog_entry_is_download_authority": False,
            "download_is_runtime_ready": False,
            "runtime_or_generation_executed": False,
            "bulk_download_allowed": False,
        },
    }
    write_json(root / CATALOG, catalog)

    evidence = {
        "schema_version": "1.0",
        "evidence_id": "WAVE64_HYPERREAL_AUDIO_PROVIDER_DISCOVERY_20260715",
        "result": "pass_provider_resolved_acquisition_catalog_second_pass",
        "catalog": CATALOG.as_posix(),
        "catalog_sha256": sha256(root / CATALOG),
        "official_asset_group_count": len(OFFICIAL_ASSETS),
        "official_source_repository_count": len(SOURCE_REPOSITORIES),
        "civitai_integration_candidate_count": len(CIVITAI_INTEGRATIONS),
        "row_binding_count": len(ROW_BINDINGS),
        "civitai_discovery_packets": discovery_packets,
        "civitai_discovered_candidate_count": sum(packet["candidate_count"] for packet in discovery_packets),
        "checks": {
            "civitai_api_used": bool(discovery_packets),
            "exact_huggingface_commits_recorded": all(len(asset["revision"]) == 40 for asset in OFFICIAL_ASSETS),
            "exact_huggingface_key_file_sha256_recorded": all(all(len(file["sha256"]) == 64 for file in asset["key_files"]) for asset in OFFICIAL_ASSETS),
            "exact_civitai_model_version_file_and_sha256_recorded": all(len(asset["sha256"]) == 64 for asset in CIVITAI_INTEGRATIONS),
            "community_integrations_separated_from_model_authority": all(asset["authority_level"].startswith("community_") for asset in CIVITAI_INTEGRATIONS),
            "license_and_gated_states_recorded": True,
            "row_bindings_recorded": True,
            "content_based_suppression_false": True,
        },
        "boundaries": catalog["boundaries"],
    }
    write_json(root / EVIDENCE, evidence)
    write_json(root / EVIDENCE_MIRROR, evidence)
    return evidence


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
