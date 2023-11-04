from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from resources.extras import FortniteInteraction

from core.errors import HTTPException
from components.view import CustomView

from discord import Button, ui


class LoginView(CustomView):

    def __init__(self, interaction: FortniteInteraction, **kwargs: float | None) -> None:
        super().__init__(interaction, **kwargs)
        self.add_item(ui.Button(label='Get Code', url=interaction.client.http_client.USER_AUTH_URL))

    @ui.button(label='Submit Code')
    async def submit_code(self, interaction: FortniteInteraction, _: Button) -> None:
        # noinspection PyUnresolvedReferences
        await interaction.response.send_modal(LoginModal(title='Authorize Account Access'))


class LoginModal(ui.Modal):

    code_field = ui.TextInput(label='Enter Auth Code', placeholder='Authorization Code', required=True)

    async def on_submit(self, interaction: FortniteInteraction) -> None:
        try:
            code = self.code_field.value
            http = interaction.client.http_client
            auth_session = await http.create_auth_session(code, interaction.user.id)
        except HTTPException:
            return await interaction.client.bad_response(interaction, 'You entered an invalid code, please try again.')

        account = await auth_session.account()
        display = account.display
        await interaction.client.send_response(interaction, f'Successfully logged in as `{display}`!')
