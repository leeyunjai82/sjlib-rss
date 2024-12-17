import requests
from bs4 import BeautifulSoup
import re
import json
import datetime

def update(category='문헌정보실 테마도서', filename='record.json'):
    try:
        # RSS 피드 URL
        rss_url = 'https://rss.blog.naver.com/sjlib24.xml'

        # 헤더 설정
        headers = {'User-Agent': 'Mozilla/5.0'}

        # 데이터를 저장할 리스트 초기화
        data_list = []

        # RSS 피드 요청
        response = requests.get(rss_url, headers=headers)
        response.raise_for_status()
        # 'lxml-xml' 파서 사용
        soup = BeautifulSoup(response.content, 'lxml-xml')

        # 게시글 목록 추출
        items = soup.find_all('item')
        if not items:
            print("RSS 피드에서 게시글을 찾을 수 없습니다.")
            exit()

        # ISO 형식의 현재 날짜 및 시간
        date = datetime.datetime.utcnow().isoformat() + 'Z'

        for item in items:
            # 게시글 정보 추출
            post_title = item.find('title').get_text(strip=True)
            post_description = item.find('description').get_text(strip=True)
            post_category = item.find('category').get_text(strip=True) if item.find('category') else '카테고리 없음'
            post_category = post_category.replace('\xa0', ' ')

            if post_category != category:
                continue

            # 정규표현식 패턴 정의
            pattern = r'\s*[가-힣]+번째 도서\s*(.*?)\s*\((.*?)\)'
            matches = re.findall(pattern, post_description)

            summary_list = []
            for match in matches:
                data = match[0].strip()
                tags = match[1]
                # 괄호와 '#' 제거하고, 쉼표로 연결
                tags = re.sub(r'[()\s#]+', ' ', tags).strip()
                tags_list = tags.split()
                tags = ', '.join(tags_list)

                summary_list.append({'data': data, 'tag': tags})

            # 데이터 리스트에 추가
            data_list.append({
                'title': post_title,
                'summary': summary_list
            })

        # 최종 데이터 구성
        output_data = {
            'category': category,
            'date': date,
            'data': data_list
        }

        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        
        return output_data
    except Exception as e:
        print(f"오류 발생: {e}")
        
        return { 
          "category": "문헌정보실 테마도서",
          "date": "2024-11-06T00:27:03.396889Z",
          "data": [
            {
              "title": "테마 오류",
              "summary": [ {"data": "도서 제목 오류", "tag": "태그오류"}]
            }
          ]
        }
      
if __name__ == "__main__":
    update()
