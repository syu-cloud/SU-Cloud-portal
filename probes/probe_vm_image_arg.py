"""C-4.5: osvm.create()의 image_id 필수 전달 검증.

검증:
1. image_id를 명시하면 create_server()까지 그대로 전달된다.
2. image_id가 None이면 ValueError로 즉시 실패한다.

실제 Nova VM은 생성하지 않는다.
"""

import os
from types import SimpleNamespace
from unittest.mock import patch

from osclient import vm as osvm


SELECTED_IMAGE_ID = "3836095d-ec16-4560-81a2-72bf810d5289"

# osvm.create()가 참조하는 최소 환경변수
TEST_ENV = {
    "SU_KEYPAIR": "test-keypair",
    "SU_FLAVOR_ID": "test-flavor",
    "SU_NETWORK_ID": "test-network",
    "SU_SECGROUP": "test-secgroup",
}


captured = {}


class FakeCompute:
    def get_keypair(self, name):
        return SimpleNamespace(public_key="ssh-rsa TEST")

    def create_server(self, **kwargs):
        # Nova에 요청하지 않고 전달된 값만 기록
        captured.update(kwargs)

        # 여기서 의도적으로 중단
        raise RuntimeError("STOP")


class FakeConn:
    compute = FakeCompute()


def test_selected_image():
    """명시한 image_id가 create_server()까지 그대로 전달되는지 확인."""

    captured.clear()

    try:
        osvm.create(
            FakeConn(),
            1,
            "/tmp/not-used",
            image_id=SELECTED_IMAGE_ID,
        )

    except RuntimeError as e:
        # FakeCompute.create_server()에서 의도적으로 발생시킨 예외만 허용
        assert str(e) == "STOP", f"예상하지 못한 RuntimeError: {e}"

    else:
        raise AssertionError("create_server()까지 도달하지 못했습니다.")

    actual = captured.get("image_id")

    print("=== image_id 전달 검증 ===")
    print("기대한 image_id :", SELECTED_IMAGE_ID)
    print("전달된 image_id :", actual)

    assert actual == SELECTED_IMAGE_ID, (
        f"image_id 불일치: expected={SELECTED_IMAGE_ID}, actual={actual}"
    )

    print("PASS — 선택한 image_id가 create_server()까지 전달됨")


def test_missing_image():
    """image_id가 없으면 fallback 없이 즉시 실패하는지 확인."""

    print("\n=== image_id 필수 검증 ===")

    try:
        osvm.create(
            FakeConn(),
            1,
            "/tmp/not-used",
            image_id=None,
        )

    except ValueError as e:
        print("발생한 예외 :", type(e).__name__, str(e))

        assert str(e) == "image_id is required", (
            f"예상하지 못한 메시지: {e}"
        )

    else:
        raise AssertionError(
            "image_id=None인데 ValueError가 발생하지 않았습니다."
        )

    print("PASS — image_id 누락 시 즉시 실패")


def main():
    # 실제 .env 값에 영향을 받지 않도록 테스트용 값으로 잠깐 덮어씀
    with patch.dict(os.environ, TEST_ENV, clear=False):
        # user_data 생성 자체는 이번 테스트 관심사가 아니므로 격리
        with patch.object(
            osvm,
            "build_user_data",
            return_value="#cloud-config\n",
        ):
            test_selected_image()
            test_missing_image()

    print("\nOK — C-4.5 probe 통과")


if __name__ == "__main__":
    main()