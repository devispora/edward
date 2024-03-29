
from requests import post

from devispora.edward_python.constants.constants import Constants
from devispora.edward_python.exceptions.rep_sheet_exceptions import RepSheetException
from devispora.edward_python.models.account_sheet import AccountSheetResult
from devispora.edward_python.models.erred_sheet import ErredSheet
from devispora.edward_python.service.helpers.discord_message_helper import shared_sheet_content, \
    share_sheet_erred_content, share_rep_erred_content

discord_webhook = f'https://discord.com/api/webhooks/{Constants.discord_webhook_id}'
staff_discord_webhook = f'https://discord.com/api/webhooks/{Constants.staff_discord_webhook_id}'


def share_sheet_to_discord(sheet: AccountSheetResult, user_ids: [int]):
    result = post(
        url=discord_webhook,
        json=shared_sheet_content(sheet, user_ids)
    )
    print(result)


def share_error_sheet_to_discord(erred_sheet: ErredSheet):
    staff_message = share_sheet_erred_content(erred_sheet)
    result = post(
        url=staff_discord_webhook,
        json=staff_message
    )
    print(result)


def share_rep_sheet_issue(rse: RepSheetException):
    result = post(
        url=staff_discord_webhook,
        json=share_rep_erred_content(rse)
    )
    print(result)
