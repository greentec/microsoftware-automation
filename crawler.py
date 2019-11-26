from bs4 import BeautifulSoup
from selenium import webdriver

options = webdriver.ChromeOptions()

driver = webdriver.Chrome('./chromedriver.exe')
driver.implicitly_wait(3)


# 로그인
url = 'http://127.0.0.1/redmine/login'
driver.get(url)

# 여기에 자신의 레드마인 ID와 패스워드를 입력한다.
driver.find_element_by_name('username').send_keys('USER_ID')
driver.find_element_by_name('password').send_keys('USER_PASSWORD')
driver.find_element_by_name('login').click()


# 구성원과 팀 찾기
profile = {}
team_list = []

url = 'http://127.0.0.1/redmine/projects/automation_demo'
driver.get(url)

html = driver.page_source
soup = BeautifulSoup(html, 'lxml')

members_box_element = soup.select('div[class*="members"]')[0]
members_element = members_box_element.select('a')
for element in members_element:
    member, team = element.text.split(' ')
    member_url = element.get('href')
    member_url = member_url.split('/')[-1]
    if team not in team_list:
        team_list.append(team)
    profile[member_url] = {'name': member, 'team': team}

print(profile)
print()


# 진행 일감
import math
import time

issues = {}

url = 'http://127.0.0.1/redmine/projects/automation_demo/issues'
driver.get(url)
html = driver.page_source
soup = BeautifulSoup(html, 'lxml')

# 진행 일감의 총 페이지 수 찾기
items_in_one_page = 25
total_elem = soup.select('span[class="items"]')[0]
max_items = total_elem.text.replace('(','').replace(')','').split('/')[-1]
max_page = math.ceil(int(max_items) / items_in_one_page)

page_url_base = 'http://127.0.0.1/redmine/projects/automation_demo/issues?page='
for page_num in range(1, max_page+1):
    url = page_url_base + str(page_num) + '&per_page=' + str(items_in_one_page)
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'lxml')

    # 일감 제목 찾기
    subject_elems = soup.select('td[class="subject"]')
    # 일감 담당자 찾기
    assigned_elems = soup.select('td[class="assigned_to"]')
    for idx, subject in enumerate(subject_elems):
        assigned_elem = assigned_elems[idx]
        href = assigned_elem.select('a')[0].get('href')
        href = href.split('/')[-1]
        if href not in profile:
            continue
        # 링크로 구성원을 찾음
        user = profile[href]
        subject_text = subject.select('a')[0].text
        subject_no = subject.select('a')[0].get('href').split('/')[-1]

        # 일감을 팀 별로 분류
        if user['team'] not in issues:
            issues[user['team']] = []
        issues[user['team']].append([int(subject_no), subject_text, user['name'], '진행'])

    time.sleep(1)

print()


# 상위 일감/하위 일감 구조 탐색
graph = {}

for team in team_list:
    print(team)
    if team in issues:
        for issue in issues[team]:
            url = 'http://127.0.0.1/redmine/issues/' + str(issue[0])
            driver.get(url)
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')

            # 일감의 위쪽에 있는 상위-하위 일감 리스트 div 를 불러온다.
            subject = soup.select('div[class="subject"]')
            if len(subject) == 0:
                continue
            subject = subject[0]

            titles = subject.div.select('a')
            issue_no_list = []
            for title in titles:
                issue_no = int(title.get('href').split('/')[-1])
                issue_no_list.append(issue_no)
            issue_no_list.append(issue[0])
            issue_no_list = [int(x) for x in issue_no_list]

            # 상위 일감/하위 일감 관계를 저장한다.
            for i in range(len(issue_no_list) - 1):
                if issue_no_list[i] not in graph:
                    graph[issue_no_list[i]] = []
                if issue_no_list[i+1] not in graph[issue_no_list[i]]:
                    graph[issue_no_list[i]].append(issue_no_list[i+1])

            time.sleep(0.01)

print(graph)
print()


# 상위 일감/하위 일감 구조 탐색
# 보여줄 일감 목록. 최상위 일감으로만 구성된다.
show_dict = {}
for team in team_list:
    show_dict[team] = []
    if team in issues:
        for issue in issues[team]:
            show_dict[team].append(int(issue[0]))

# 최상위 일감이 아닌 일감 목록
delete_dict = {}
for team in team_list:
    delete_dict[team] = []

# 상위 일감의 하위 일감이 같은 팀에 있을 때에만 하위 일감을 show_dict 에서 지운다.
for team in show_dict:
    for issue in show_dict[team]:
        if issue in graph:
            for sub_issue in graph[issue]:
                if sub_issue in show_dict[team]:
                    if sub_issue not in delete_dict[team]:
                        delete_dict[team].append(sub_issue)

for team in delete_dict:
    for issue in delete_dict[team]:
        show_dict[team].remove(issue)

print(delete_dict)
print(show_dict)
print()


# 템플릿 텍스트 생성
import html
from jinja2 import Template
show_team_list = ['시스템기획', '콘텐츠기획', '밸런스기획', '클라이언트프로그래밍', '서버프로그래밍']

template = Template(u'''\
{%- macro dump_sub_issues(indexes, team) %}
  <ul>
    {% for idx in indexes %}
      {% if idx not in show_dict[team] %}
        {% for issue in issues[team] %}
          {% if issue[0] == idx %}
            <li><a href="http://127.0.0.1/redmine/issues/{{issue[0]}}">#{{ issue[0] }}</a> {{ html.escape(issue[1]) }} ({{ issue[-1] }})</li>
            {% if issue[0] in graph %}
              {% call dump_sub_issues(graph[issue[0]], team) %}
              {% endcall %}
            {% endif %}
          {% endif %}
        {% endfor %}
      {% endif %}
    {% endfor %}
  </ul>
  {{ caller() }}
{%- endmacro %}
<h2>
  <strong>➢ 팀별 금주 주간 업무</strong>
</h2>
<ul>
  {%- for team in show_team_list %}
    <li>
      <p>{{ team }}</p>
      <ul>
        {%- for issue in issues[team] %}
          {% if issue[0] in show_dict[team] %}
            <li><a href="http://127.0.0.1/redmine/issues/{{issue[0]}}">#{{ issue[0] }}</a> {{ html.escape(issue[1]) }} ({{ issue[-1] }})</li>
            {% if issue[0] in graph %}
              {% call dump_sub_issues(graph[issue[0]], team) %}
              {% endcall %}
            {% endif %}
          {% endif %}
        {% endfor %}
      </ul>
    </li>
  {%- endfor %}
</ul>

''')

s = template.render(show_team_list=show_team_list,
                    issues=issues,
                    html=html,
                    graph=graph,
                    show_dict=show_dict)

import re
s = re.sub('\n', '', s)
s = re.sub(' +', ' ', s)

print(s)
