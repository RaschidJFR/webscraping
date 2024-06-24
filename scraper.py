import requests
from bs4 import BeautifulSoup
import sys
import dns.resolver
from tldextract import extract

def _get_domain(url) -> str:
 tsd, td, tsu = extract(url)
 return f"{td}.{tsu}"

class ResponseResults:
    
  def _redirect_occurred(response:requests.Response) -> bool:
      if response.history:
          original_domain = _get_domain(response.url)
          redirect_domain = _get_domain(response.history[-1].url)

          return original_domain != redirect_domain
      return False
  
  def __init__(self, response:requests.Response):
    self.http_status_code = response.status_code
    self.redirect_domain = ''
    self.redirect_url = ''
    self.error = ''

    if ResponseResults._redirect_occurred(response):
      self.redirect_url = response.url
      self.redirect_domain = _get_domain(response.url)
    
    try:
      response.raise_for_status()
    except requests.exceptions.HTTPError as e:
      self.error = str(e)
    
    
class WebsiteScraper:
  
  def __init__(self, url:str, model):
    self._url = url if url.startswith(('http://', 'https://')) else 'https://' + url
    self._model = model
    self._domain = _get_domain(url)
    self._is_domain_active: bool = None
    self._is_connection_ok: bool = None
    self._response: ResponseResults = None
    self._text: str = None
    self._summary: str = None
  
  def is_domain_active(url):
      domain = _get_domain(url)
      try:
          dns.resolver.resolve(domain, 'A')
          return True
      except dns.resolver.NXDOMAIN:
          return False
      except dns.resolver.Timeout:
          return False
      except dns.resolver.NoAnswer:
          return False
      except Exception as e:
          print (e)
          return False
        
  def _extract_text_from_html(html, debug=False):
      soup = BeautifulSoup(html, 'html.parser')
      
      # Ignore link text
      for a in soup.find_all('a'):
        a.decompose()
      
      text = soup.get_text(separator='\n')
      
      if debug:
          with open('temp.txt', 'w') as file:
              file.write(text)
      
      return text
  

  def scrape_text(self, debug=False):
    url = self._url
    self._is_domain_active = WebsiteScraper.is_domain_active(url)
    if not self._is_domain_active:
      return
      
    try:
      response = requests.get(url, allow_redirects=True, timeout=10)
      self._is_connection_ok = True        
    except requests.exceptions.Timeout as e:
      self._is_connection_ok = False
      return
    except Exception as e:
      print(e, file=sys.stderr)
      self._is_connection_ok = False
      return
    
    self._response = ResponseResults(response)
    if self._response.error:
      return ''
    
    html = response.text
    
    if debug:
      with open('temp.html', 'w') as file:
          file.write(html)

    self._text = WebsiteScraper._extract_text_from_html(html, debug)
    return self._text

  def generate_summary(self, debug=False):
    summary: str = ''
    try:
      if not self._is_domain_active:
        summary = "[Domain inactive]"
      elif not self._is_connection_ok:
        summary = "[Website server unreachable]"
      else: 
        
        if debug and self._response.redirect_domain:
          print(f"Redirect: {self._domain} -> {self._response.redirect_domain}")
              
        code = self._response.http_status_code
        if code == 404:
          summary = "[Website not found]"
        elif code == 403 or code == 406:
          summary = "[Website scraping blocked]"
        elif code >= 502 and code < 600:
          summary = "[Website not working]"
        elif code > 400:
          print(self._response.error)
          summary = ''
        elif self._text:
          if self._response.redirected_domain: summary = f"[{self._response.redirected_domain}] "
          summary += self._model.summarize(self._text)
        else:
          print(f"No text fetched for {self._domain}")
        
    except Exception as e:
      print(e, file=sys.stderr)
      summary = ''
    finally:
      self._summary = summary
      return self._summary