from abc import get_cache_token
import collections
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
from typing import NamedTuple
import PyPDF2
import urllib.request
import warnings
import collections


class Paper(NamedTuple):
    id: str
    website: str
    venue: str
    title: str
    url: str
    year: int


def get_icml_papers():
    offset = 0
    while True:
        url = f'https://api.openreview.net/notes?invitation=ICLR.cc%2F2021%2FConference%2F-%2FBlind_Submission&details=replyCount%2Cinvitation%2Coriginal%2CdirectReplies&limit=1000&offset={offset}'
        html = urllib.request.urlopen(url).read()
        data = json.loads(html)
        notes = data['notes']
        if not notes:
            return
        for note in notes:
            id = note['id']
            title = note['content']['title']
            created = datetime.fromtimestamp(note['tcdate']//1000)
            url = f'https://openreview.net/pdf?id={id}'
            yield Paper(id=id, website='openreview', venue='icml2021', title=title, url=url, year=created.year)
        offset += 1000


def get_neurips_papers(year: int):
    url = f'https://papers.nips.cc/paper/{year}'
    html = urllib.request.urlopen(url).read()
    html = str(html)
    matches = re.findall('hash/([a-f0-9]+)-Abstract.html">(.+?)<', html)
    for id, title in matches:
        url = f'https://papers.nips.cc/paper/{year}/file/{id}-Paper.pdf'
        yield Paper(id=id, website='neurips', venue='NeurIPS', title=title, url=url, year=year)


def get_pdf_pages(url, filepath):
    path = Path(filepath)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(url).read()
        with path.open('wb') as f:
            f.write(data)
    fr = path.open('rb')
    warnings.filterwarnings('ignore')
    reader = PyPDF2.PdfFileReader(fr)
    texts = []
    for i in range(0, reader.numPages):
        page = reader.getPage(i)
        text = page.extractText()
        texts.append(text)
    return texts


def check_keywords(pages, keywords):
    matches = collections.defaultdict(list)
    for i, page in enumerate(pages):
        for keyword in keywords:
            if keyword in page.lower():
                matches[keyword].append(i)
    return dict(matches)


general_keywords = ['mechanical turk', 'mturk', 'prolific', 'crowd', 'rater', 'annotator', 'participant',  'amt', 'labeller', 'labeler', 'figure eight']

papers = list(get_neurips_papers(2021))
print('Total submissions: {}\n'.format(len(papers)))
f = open('output1.csv', 'w')
f.write('Item Title\tPublication Title\tYear\tURL\tMeet criteria\tIRB?\tPayment?\tConsent?\tDemographic?\tOther?\n')
f.flush()
for paper in papers:
    try:
        pages = get_pdf_pages(paper.url, f'data/{paper.website}/{paper.id}.pdf')
    except:
        print(f'{paper.id}\t{paper.title}\n')
        pass
    else:
        meet_criteria = len(check_keywords(pages, general_keywords)) > 0
        irb, payment, consent, demographic, other = '', '', '', '', ''
        if meet_criteria:
            irb = check_keywords(pages, ['irb', 'review board', 'committee', 'approved'])
            payment = check_keywords(pages, ['$', 'paid', 'payment', 'cents', 'compensated'])
            consent = check_keywords(pages, ['consent'])
            demographic = check_keywords(pages, ['demographic', 'male', ' age '])
            other = check_keywords(pages, ['ethic'])
        meet_criteria = 'Yes' if meet_criteria else 'No'
        print(f'{paper.id}\t{paper.title}\t{meet_criteria}')
        f.write(f'{paper.title}\t{paper.venue}\t{paper.year}\t{paper.url}\t{meet_criteria}\t{irb}\t{payment}\t{consent}\t{demographic}\t{other}\n')
        f.flush()
