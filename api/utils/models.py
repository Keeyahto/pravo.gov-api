import json
from pydantic import BaseModel, Field, validator
from pathlib import Path


class Person(BaseModel):
    raw_name: str = ''
    lemm_name: str = ''
    gender:str = ''
    fio: dict = {}

    @validator('raw_name', pre=True)
    def pre_prep(cls, v):
        return ' '.join(v.split())

class AppoitmentLine(BaseModel):
    raw_line: str|None = ''
    appointees: list[Person] = [] # список людей, которых назначили 
    resignees: list[Person] = []
    position: str|None = ''
    # TODO: action
    # action: str|None = None # appoint, resign



class FileData(BaseModel):
    doc_id:str=None
    file_name : str = None
    file_path : str|Path = None
    date : str = None
    text_raw : str|None = None
    splitted_text:list[str]=None
    url : str = None
    appointment_lines: list[AppoitmentLine] = [] # events
    author:str = None # кто подписал
    naznach_line:str = None
    


if __name__ == '__main__':
    d = {'link':'its a link!'}
    model = FileData(doc_id=1111111) 
    temp = model.dict()
    total = temp | d
    print(total)
    # total = {**temp, **d}

    # d.update(**temp)
    # print(d)
    # print(FileData(**d))
    
    # f = r'C:\Users\ironb\прогр\Declarator\appointment-decrees\data\РФ\parsed\parsed.json'
    # with open(f,encoding='utf-8') as f:
#     f_d = FileData(**json.load(f)[0])
    # print(FileData.schema_json(indent=3))
    # with open('schema.json', 'w') as f:
    #     json.dump(FileData.schema_json(indent=3), f)
    # print()
        # print((f_d))



    # f = FileData()
    # print(schema_json_of(f.json()))
    # file_data = FileData(file_name = '-1--21_01_2002.rtf', date='21-01-2002',
    #                     file_path='C:\\Users\\ironb\\прогр\\Declarator\\appointment-decrees\\downloads\\regions\\ивановская область\\raw_files\\-1--21_01_2002.rtf')
    #
    # line = {'raw_line': '      1.   Назначить   руководителем   областной   целевой   программы\n"Патриотическое  воспитание  граждан Российской Федерации в Ивановской\nобласти   на   период   до   2005  года"  Зимина  Николая  Васильевича\nзаместителя главы администрации Ивановской области.\n',
    # 'names': [{'name_raw': 'Зимина  Николая  Васильевича', 'name_norm': 'Зимин  Николай  Васильевич'}], 'position': 'руководителем областной целевой программы "патриотическое воспитание граждан российской федерации ивановской области период до года" заместителя главы администрации ивановской области'}
    #
    #
    # data = {'file_name': '-101--12_04_2001.rtf', 'file_path': 'downloads\\regions\\ивановская область\\raw_files\\-101--12_04_2001.rtf', 'date': '12-04-2001', 'text_raw': 'Назначить  Степанова  Юрия  Валентиновича  начальником управления промышленности  администрации Ивановской области с 09 апреля 2001 г. с должностным  окладом  согласно штатному расписанию, в порядке перевода из  управления  экономики  и  прогнозирования администрации Ивановской области,  освободив  от  должности начальника  отдела государственных поставок  и  лицензирования  управления  экономики  и  прогнозирования администрации Ивановской области.', 'link': 'http://pravo.gov.ru/proxy/ips/?savertf=&link_id=0&nd=107011781&intelsearch=%CD%E0%E7%ED%E0%F7%E8%F2%FC++%D1%F2%E5%EF%E0%ED%EE%E2%E0++%DE%F0%E8%FF++%C2%E0%EB%E5%ED%F2%E8%ED%EE%E2%E8%F7%E0++%ED%E0%F7%E0%EB%FC%ED%E8%EA%EE%EC+%F3%EF%F0%E0%E2%EB%E5%ED%E8%FF&firstDoc=1&page=all', 'appointment_lines': [{'raw_line': '     Назначить  Степанова  Юрия  Валентиновича  начальником управления\nпромышленности  администрации Ивановской области с 09 апреля 2001 г. с\nдолжностным  окладом  согласно штатному расписанию, в порядке перевода\nиз  управления  экономики  и  прогнозирования администрации Ивановской\nобласти,  освободив  от  должности  начальника  отдела государственных\nпоставок  и  лицензирования  управления  экономики  и  прогнозирования\nадминистрации Ивановской области.\n', 'names': [{'name_raw': 'Степанова  Юрия  Валентиновича', 'name_norm': 'Степанов  Юрий  Валентинович'}], 'position': 'начальником управления промышленности администрации ивановской области'}]}
    #
    # res = FileData(**data).dict()
    #
    # with open('test_file.json', 'w') as f:
    #     json.dump(res,f)
    #
    # # with open('decrees_schema.json', 'w') as f:
    # #     f.write(FileData.schema_json())
    #
    # # print()
    #
    # # appo_line = AppoitmentLine(**line)
    # file_data.appointment_lines = appo_line
    # # print(FileData.schema_json)
    # js = file_data.dict()
    # print(js)
    # import json
    # print(js.encode().decode())


    # file_data.appointment_lines.append('!')

    # print(appo_line)
