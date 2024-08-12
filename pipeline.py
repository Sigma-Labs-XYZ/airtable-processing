import os
from dotenv import load_dotenv

from pyairtable import Api


load_dotenv()
ACCESS_TOKEN = os.environ['AIRTABLE_ACCESS_TOKEN']
BASE_ID = os.environ['BASE_ID']


def extract_interviews(fields: dict) -> list:
    interviews = []
    for (field, value) in fields.items():
        if 'Client' in field:
            num = field.split(' ')[-1]
            status = fields.get('Status ' + num)
            interviews.append({
                'Email': fields.get('Name'),
                'Cohort': fields.get('Cohort'),
                'Company': value,
                'Outcome': status,
                'Style of Interview': "Unknown"
            })
    return interviews


def normalise_and_explode_interview(interview: dict):
    outcome = interview['Outcome']

    if not outcome:
        return []

    if outcome in ['Offer', 'Withdrawn', 'Stage 1', 'S1-Rejected', 'S1-Progress', "Turned down"]:
        interview['Round'] = 'Stage 1'
        if outcome == 'Stage 1':
            interview['Round'] = 'Stage 1'
            interview['Outcome'] = "Pending"
        elif outcome == 'S1-Rejected':
            interview['Round'] = 'Stage 1'
            interview['Outcome'] = 'Fail'
        elif outcome == 'S1-Progress':
            interview['Round'] = 'Stage 1'
            interview['Outcome'] = 'Progress'
        elif outcome == 'Turned down':
            interview['Round'] = 'Unknown Stage'
            interview['Outcome'] = 'Turned down'
        elif outcome == "Offer":
            interview['Round'] = 'Unknown Stage'
            interview['Outcome'] = 'Offer'
        return []

    if 'Stage' in outcome:
        stage_num = int(outcome.split(" ")[1])
        interview['Round'] = outcome
        interview['Outcome'] = "Pending"
    else:
        stage_num = int(outcome.split("-")[0][1:])
        interview['Round'] = f'Stage {stage_num}'
        if 'Rejected' in outcome:
            interview['Outcome'] = 'Fail'
        else:
            interview['Outcome'] = 'Progress'

    previous_interview = {}
    for (field, value) in interview.items():
        previous_interview[field] = value
    previous_interview['Outcome'] = f'S{stage_num - 1}-Progress'

    return [previous_interview]


def main():
    api = Api(ACCESS_TOKEN)
    summary_table = api.table(BASE_ID, 'Summary')
    tracker_table = api.table(BASE_ID, 'Interview Tracker')

    print(ACCESS_TOKEN, BASE_ID)

    summary_records = []
    table_iter = summary_table.iterate()
    while True:
        try:
            summary_records += next(table_iter)
        except StopIteration:
            break

    interviews = []
    for row in summary_table.all():
        interviews += extract_interviews(row['fields'])

    for interview in interviews:
        interviews += normalise_and_explode_interview(interview)

    interviews = filter(lambda interview: interview['Outcome'], interviews)
    interviews = sorted(interviews, key=lambda interview: [
                        interview['Email'], interview['Round']])

    # Less efficient than batch_create, but keeps the records in a logical order in views!
    for interview in interviews:
        print(interview)
        print(tracker_table.create(interview, typecast=True))


if __name__ == "__main__":
    main()
