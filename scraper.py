import requests
from bs4 import BeautifulSoup
import sys
import dns.resolver
from tldextract import extract

def _get_domain(url) -> str:
 tsd, td, tsu = extract(url)
 return f"{td}.{tsu}"

class RedirectReport:
    
  def _redirect_occurred(response:requests.Response) -> bool:
      if response.history:
          original_domain = _get_domain(response.url)
          redirect_domain = _get_domain(response.history[-1].url)

          return original_domain != redirect_domain
      return False
  
  def __init__(self, response:requests.Response):
    self.status_code = response.status_code
    self.redirected_domain = ''
    self.redirected_url = ''
    self.error = ''

    if RedirectReport._redirect_occurred(response):
      self.redirected_url = response.url
      self.redirected_domain = _get_domain(response.url)
      self.status_code = response.history[-1].status_code
    
    try:
      response.raise_for_status()
    except requests.exceptions.HTTPError as e:
      self.error = str(e)
    
class ConnectivityReport:
  def __init__(self):
    self.is_domain_active:bool = None
    self.is_server_reachable:bool = None
    self.redirect_report:RedirectReport = None
    self.status_code:int = None
    
  @property
  def is_redirecting(self):
    if not self.redirect_report:
      return None
    else:
      return bool(self.redirect_report.redirected_domain)
    
class WebsiteScraper:
  
  def __init__(self, url:str, model):
    self._url = url if url.startswith(('http://', 'https://')) else 'https://' + url
    self._model = model
    self._domain = _get_domain(url)
    self.connectivity_report = None
    self._text: str = None
    self._summary: str = None
  
  def check_domain_active(url):
      """
      Checks if the domain of the given URL is active by attempting to resolve its DNS 'A' record.

      Args:
      url (str): The URL whose domain's DNS records are to be checked.

      Returns:
      bool: True if the domain has an 'A' record, indicating it is active. False otherwise.
      """
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
          print(e)
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
  
  def test_website_connectivity(self):
    url = self._url
    report = ConnectivityReport()
    report.is_domain_active = WebsiteScraper.check_domain_active(url)
    if report.is_domain_active:
  
      try:
        httpResponse = requests.head(url, allow_redirects=True, timeout=10)
        report.status_code = httpResponse.status_code
        report.is_server_reachable = True
        report.redirect_report = RedirectReport(httpResponse)
      except requests.exceptions.Timeout as e:
        report.is_server_reachable = False
      except Exception as e:
        print(e, file=sys.stderr)
        report.is_server_reachable = False
    
    self.connectivity_report = report
    return report

  def scrape_text(self, debug=False):
    html = ''
    connectivity = self.test_website_connectivity()
    
    if connectivity.is_server_reachable:
      response = requests.get(self._url, allow_redirects=True, timeout=10)
      html = response.text
    
    if debug:
      with open('temp.html', 'w') as file:
          file.write(html)

    self._text = WebsiteScraper._extract_text_from_html(html, debug)
    return self._text

  def generate_summary(self, debug=False):
    summary: str = ''
    if not self.connectivity_report:
      raise('You must first call test_website_connectivity()')
    
    try:
      if not self.connectivity_report.is_domain_active:
        summary = "[Domain inactive]"
      elif not self.connectivity_report.is_server_reachable:
        summary = "[Website server unreachable]"
      else: 
        
        redirect = ''
        if debug and self.connectivity_report.is_redirecting:
          redirect = self.connectivity_report.redirect_report.redirected_domain
          print(f"Redirect: {self._domain} -> {redirect}")
              
        code = self.connectivity_report.status_code
        if code == 404:
          summary = "[Website not found]"
        elif code == 403 or code == 406:
          summary = "[Website scraping blocked]"
        elif code >= 502 and code < 600:
          summary = "[Website not working]"
        elif code >= 400:
          print(self.connectivity_report.redirect_report.error)
          summary = ''
        elif self._text:
          if redirect: summary = f"[{redirect}] "
          summary += self._model.summarize(self._text)
        else:
          print(f"No text fetched for {self._domain}")
        
    except Exception as e:
      print(e, file=sys.stderr)
      summary = ''
    finally:
      self._summary = summary
      return self._summary