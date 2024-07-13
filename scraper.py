import requests
from bs4 import BeautifulSoup
from sys import stderr
import dns.resolver
from tldextract import extract

def _get_domain(url) -> str:
  """Extract the domain from a url."""
  _, td, tsu = extract(url)
  return f"{td}.{tsu}"

class RedirectReport:
  """Data structure to store information about redirects"""
    
  def _redirect_occurred(response:requests.Response) -> bool:
      if response.history:
          original_domain = _get_domain(response.history[0].url)
          redirect_domain = _get_domain(response.url)

          return original_domain != redirect_domain
      return False
  
  def __init__(self, response:requests.Response):
    self.status_code = response.status_code
    """Status code of the last redirect (before the end destination). Empty if there was no redirect."""
    self.redirected_domain = ''
    """The final domain to which the request was redirected to. Empty if there was no redirect."""
    self.redirected_url = ''
    """The final url to which the request was redirected to. Empty if there was no redirect."""

    if RedirectReport._redirect_occurred(response):
      self.redirected_url = response.url
      self.redirected_domain = _get_domain(response.url)
      self.status_code = response.history[-1].status_code
    
class ConnectivityReport:
  
  def __init__(self, url:str):
    self.url:str = url
    """Original url to test."""
    self.is_domain_active:bool = None
    """`True` if the domain could be resolved."""
    self.is_server_reachable:bool = None
    """`True` if an HTTP request was retrieved regardless of its status code."""
    self.is_website_accessible:bool = None
    """`True` if a response with no error was received."""
    self.redirect_report:RedirectReport = None
    """Data structure to store information about redirects."""
    self.status_code:int = None
    """Final status code after all redirects."""
    self.error: str = None
    """Final error messsage after all redirects."""
  
  def __str__(self) -> str:
    return self._decode()
  
  @property
  def domain(self) -> str:
    return _get_domain(self.url)
    
  @property
  def is_redirecting(self):
    """Return `True` if a main domain redirect is detected.
    TODO: Distinguish between domain, subdomain, and path redirects.
    """
    if not self.redirect_report:
      return None
    else:
      return bool(self.redirect_report.redirected_domain)
    
  def _decode(self) -> str:
    """Returns a human-readable summary of the report
    
    Used under the hood for `str(ConnectivityReport)`
    """
    result_msg: str = ''
    
    try:
      if not self.is_domain_active:
        result_msg = "[Domain inactive]"
      else:
        
        if self.is_redirecting:
          redirect = self.redirect_report.redirected_domain
          result_msg = f"[{self.domain} -> {redirect}]: "
        
        if not self.is_server_reachable:
          result_msg += "[Server unreachable]"
        elif not self.is_website_accessible:
          result_msg += f"[Site inaccessible: {self.error}]"

        else:
          result_msg += "[Site accessible: OK]"
        
    except Exception as e:
      print(e)
      result_msg = '[Unknown Error]'
    finally:
      return result_msg
    
class WebsiteScraper:
  _agent = "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
  _headers={"User-Agent": f"{_agent}"}
  
  def __init__(self, url:str):
    self._url = url if url.startswith(('http://', 'https://')) else 'https://' + url
    self.connectivity_report = None
  
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
        
  def _extract_text_from_html(html):
      soup = BeautifulSoup(html, 'html.parser')
      
      # Ignore link text
      for a in soup.find_all('a'):
        a.decompose()
      
      text = soup.get_text(separator='\n')      
      return text
  
  def test_connectivity(self):
    """
    Tests the connectivity of the website by checking the domain's activity and server's response.

    This method first checks if the domain of the URL is active. If active, it attempts to connect
    to the server using a HEAD request to minimize data transfer. If the HEAD request fails due
    to an HTTP error, a GET request is attempted. 
    
    The method updates the `connectivity_report` attribute of the instance with the results.

    Returns:
      ConnectivityReport: An object containing details about the connectivity test, including
      whether the domain is active, the server is reachable, any redirections, and if the website
      is accessible without errors.
    """
    url = self._url
    report = ConnectivityReport(url)
    report.is_domain_active = WebsiteScraper.check_domain_active(url)
    if report.is_domain_active:
  
      try:
        httpResponse = requests.head(url, allow_redirects=True, timeout=10, headers=self._headers)
        report.is_server_reachable = True
        try:
          httpResponse.raise_for_status()
        except requests.exceptions.HTTPError as e:
          try:
            # 405 is common in parked domains
            if httpResponse.status_code == 405: raise e
            
            # try a different method
            httpResponse = requests.get(url, allow_redirects=True, timeout=10, headers=self._headers)
            httpResponse.raise_for_status()
          except requests.exceptions.HTTPError as e:
            report.error = str(e)
        
        report.status_code = httpResponse.status_code
        report.redirect_report = RedirectReport(httpResponse)
        report.is_website_accessible = not bool(report.error)
        
      except requests.exceptions.Timeout as e:
        report.is_server_reachable = False
      except Exception as e:
        print(e, file=stderr)
        report.is_server_reachable = False
    
    self.connectivity_report = report
    return report

  def scrape_text(self) -> str:
    """Test connectivity and extract a plan text from the website's HTML
    
    The function `test_connectivity()` will be called if it hasn't been called before.
    
    Returns:
      str: The text extracted from the HTML or an empty string if a connectivity issue was found.
    """
    html = ''
    connectivity = self.connectivity_report
    if not connectivity:
      connectivity = self.test_connectivity()
    
    if connectivity.is_website_accessible:
      response = requests.get(self._url, allow_redirects=True, timeout=10, headers=self._headers)
      html = response.text
      
    return WebsiteScraper._extract_text_from_html(html)
