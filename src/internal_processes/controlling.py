import logging
from src.internal_apis.models import Control, is_younger_than, TaskControl
from src.internal_apis.database import insert_one_object_into_db, select_from_db
from decimal import Decimal
from time import time
from uuid import uuid4


class InvalidSettingRetry(Exception):
    def __init__(self, message="Retried setting to no effect"):
        self.message = message
        super().__init__(self.message)


def create_and_save_control(control_temperature: str) -> Control:
    logging.info('saving control')
    control = Control(
        id=str(uuid4()),
        timestamp=int(time()),
        target_setpoint=control_temperature)
    insert_one_object_into_db(control, Control.__tablename__)
    return control


def retrieve_recent_control_temperature(control_ids: list) -> Decimal:
    logging.info('retrieving relevant controls')

    def check_for_control_errors(checked_controls: list[Control]):
        logging.info('checking for errors')
        points = [c.target_setpoint for c in checked_controls]
        logging.info(f'''executed controls: {str(points)[1:-1].replace("'", "")}''')
        if len(points) >= 4:
            if points[-1] == points[-2] == points[-3] == points[-4]:
                raise InvalidSettingRetry

    all_task_controls = [
        Control(**control) for control in
        select_from_db(Control.__tablename__, where_in={'id': control_ids}, keys=True)]
    logging.info(f'all task controls {len(all_task_controls)}')
    for cont in all_task_controls:
        logging.info(f'{cont.get_log_info()}')

    check_for_control_errors(all_task_controls)
    recent_timestamp = max(c.timestamp for c in all_task_controls)
    recent_temperature_control = [
        c.target_setpoint for c in all_task_controls
        if c.timestamp == recent_timestamp and is_younger_than(c.timestamp)].pop()

    logging.info(f'recent temperature control set point value {recent_temperature_control}')

    return Decimal(recent_temperature_control)


def retrieve_which_controls(task_id: str) -> list[str]:
    return select_from_db(table_name=TaskControl.__tablename__,
                          columns=['control_id'],
                          where_equals={'task_id': task_id},
                          keys=False)


def create_task_control_pairing(performed_task_control: Control, related_task_id: str):
    logging.info('pairing setting with created control')
    performed_control_relationship = TaskControl(
        control_id=performed_task_control.id,
        task_id=related_task_id)
    insert_one_object_into_db(performed_control_relationship, TaskControl.__tablename__)