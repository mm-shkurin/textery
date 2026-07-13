class RegisterUser:
    async def execute(self, email: str, password: str, confirm_password: str) -> None:
        raise NotImplementedError()
