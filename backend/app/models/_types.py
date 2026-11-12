from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls, length: int = 20):
    """Enum을 MySQL ENUM이 아닌 VARCHAR로 저장 (값 추가 시 마이그레이션 부담 감소)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
