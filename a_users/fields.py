from fernet_fields import EncryptedTextField
from cryptography.fernet import InvalidToken

class FallbackEncryptedTextField(EncryptedTextField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return super().from_db_value(value, expression, connection)
        except InvalidToken:
            return value