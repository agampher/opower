import asyncio
from datetime import datetime, timedelta
import logging
import os
from getpass import getpass
from typing import Optional

import aiohttp

from opower import (
    AggregateType,
    Opower,
    ReadResolution,
    get_supported_utilities,
    select_utility,
)

def get_env_var_or_default(env_var, default):
    return os.getenv(env_var, default)

def get_env_var(env_var):
    return os.getenv(env_var)

async def _main() -> None:
    # logging
    verbose = int(get_env_var_or_default('VERBOSE', 0))
    logging.basicConfig(level=logging.DEBUG - verbose * 10 + 1 if verbose > 0 else logging.INFO)

    # environment variables
    supported_utilities = [utility.__name__.lower() for utility in get_supported_utilities()]
    utility = get_env_var('UTILITY') or input(f"Utility, one of {supported_utilities}: ")
    username = get_env_var('USERNAME') or input("Username: ")
    password = get_env_var('PASSWORD') or getpass("Password: ")
    mfa_secret = get_env_var('MFA_SECRET') or (input("2FA secret: ") if select_utility(utility).accepts_mfa() else None)
    aggregate_type = AggregateType[get_env_var_or_default('AGGREGATE_TYPE', 'DAY').upper()]
    start_date = datetime.fromisoformat(get_env_var_or_default('START_DATE', (datetime.now() - timedelta(days=1)).isoformat()))
    end_date = datetime.fromisoformat(get_env_var_or_default('END_DATE', datetime.now().isoformat()))
    usage_only = get_env_var_or_default('USAGE_ONLY', 'false').lower() in ('true', '1', 'yes')

    async with aiohttp.ClientSession() as session:
        opower = Opower(session, utility, username, password, mfa_secret)
        await opower.async_login()
        # for forecast in await opower.async_get_forecast():
        #     print("\nCurrent bill forecast:", forecast)
        for account in await opower.async_get_accounts():
            if (aggregate_type == AggregateType.HOUR and account.read_resolution == ReadResolution.DAY):
                aggregate_type = AggregateType.DAY
            elif (aggregate_type != AggregateType.BILL and account.read_resolution == ReadResolution.BILLING):
                aggregate_type = AggregateType.BILL
            # print(f"\nGetting historical data: account={account}, aggregate_type={aggregate_type}, start_date={start_date}, end_date={end_date}")
            prev_end: Optional[datetime] = None
            data_method = opower.async_get_usage_reads if usage_only else opower.async_get_cost_reads
            data = await data_method(account, aggregate_type, start_date, end_date)
            
            for read in data:
                start_minus_prev_end = None if prev_end is None else read.start_time - prev_end
                end_minus_prev_end = None if prev_end is None else read.end_time - prev_end
                prev_end = read.end_time
                print_data = f"{read.start_time}\t{read.end_time}\t{read.consumption}\t"
                # print_data += f"{getattr(read, 'provided_cost', '')}\t{start_minus_prev_end}\t{end_minus_prev_end}"
                print_data += f"{getattr(read, 'provided_cost', '')}"
                print(print_data)
            print()

asyncio.run(_main())
