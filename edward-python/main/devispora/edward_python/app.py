import json
from typing import List

from pytz import utc
from datetime import datetime

from devispora.edward_python.constants.constants import Constants
from devispora.edward_python.exceptions.account_sheet_exceptions import AccountSheetException, \
    AccountSheetExceptionMessage
from devispora.edward_python.exceptions.rep_sheet_exceptions import RepSheetException
from devispora.edward_python.exceptions.sheet_share_exception import SheetShareException
from devispora.edward_python.models.account_sheet import AccountSheetStatus
from devispora.edward_python.models.contact_sheet import Contact
from devispora.edward_python.models.erred_sheet import ErredSheet
from devispora.edward_python.models.helpers.contact_sheet_helper import find_reps_on_sheet, fetch_emails_only, \
    fetch_discord_ids
from devispora.edward_python.models.helpers.date_helper import retrieve_current_date
from devispora.edward_python.service.discord_interaction_service import share_sheet_to_discord, \
    share_error_sheet_to_discord, share_rep_sheet_issue
from devispora.edward_python.service.drive_interaction_service import retrieve_items_from_folder, share_sheet_to_users
from devispora.edward_python.service.helpers.google_item_helper import filter_to_just_files, \
    filter_by_name_and_cooldown, filter_by_share_and_cleaning
from devispora.edward_python.service.rep_interaction_service import retrieve_contacts
from devispora.edward_python.service.sheets_interaction_service import retrieve_sheet_information, update_shared_status


just_this_folder = Constants.ovo_drive_folder
contact_sheet = Constants.ovo_drive_rep_sheet


def lambda_handler(event, context):
    current_date_utc = retrieve_current_date()
    print(f'starting at {current_date_utc}')
    try:
        contact_reps = retrieve_contacts(contact_sheet)
        start_processing(current_date_utc, contact_reps)
    except RepSheetException as rse:
        share_rep_sheet_issue(rse)
        print(rse)


    # non aws-devs: event/context are mandatory even if not used

    # todo
    #  Clean/error mechanism ->
    #   - bundle up cleaned sheets + link/name
    #  Bonus ->
    #   - Show friendlier name instead of service account gibberish.
    #   - validate email again with some room of split-character-improvement?
    finish_date = datetime.now(tz=utc)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f'Started at {current_date_utc} and finished at {finish_date}',
        }),
    }


def start_processing(current_date_utc: datetime, contact_reps: List[Contact]):
    drive_items = retrieve_items_from_folder(just_this_folder)
    filtered_files = filter_to_just_files(drive_items)

    filtered_sheets = filter_by_name_and_cooldown(filtered_files, current_date_utc)

    converted_sheets, erred_sheets = retrieve_sheet_information(filtered_sheets)
    sheets_to_share, sheets_to_clean = filter_by_share_and_cleaning(converted_sheets, current_date_utc)

    for sheet in sheets_to_share:
        approved_contacts = find_reps_on_sheet(contact_reps, sheet)
        to_share_emails = fetch_emails_only(approved_contacts)
        try:
            share_sheet_to_users(sheet.sheet_id, to_share_emails)
        except SheetShareException as sse:
            erred_sheets.append(ErredSheet(sheet.sheet_id, sheet.sheet_name, AccountSheetException(sse)))
            continue
        default_range = 'B4'
        if len(to_share_emails) > 0:
            update_shared_status(sheet.sheet_id, default_range, AccountSheetStatus.StatusShared)
            retrieved_discord_ids = fetch_discord_ids(approved_contacts)
            share_sheet_to_discord(sheet, retrieved_discord_ids)
            if len(sheet.emails) != len(to_share_emails):
                erred_sheets.append(
                    ErredSheet(
                        sheet.sheet_id, sheet.sheet_name,
                        AccountSheetException(AccountSheetExceptionMessage.EmailNotFoundInRepSheet)
                    )
                )
        else:
            erred_sheets.append(
                ErredSheet(
                    sheet.sheet_id, sheet.sheet_name,
                    AccountSheetException(AccountSheetExceptionMessage.EmailNeverMatched)
                )
            )
    for sheet in erred_sheets:
        share_error_sheet_to_discord(sheet)