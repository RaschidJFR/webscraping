import unittest
from requests import HTTPError
from unittest.mock import patch, Mock
from scraper import RedirectReport, WebsiteScraper

class TestRedirectReport(unittest.TestCase):

  def setUp(self):
    return

  def test_catch_redirect(self):
    url = "https://abc.com"
    redirect_url = "https://xyz.net"
    
    response = Mock()
    response.status_code = 301
    response.history = [Mock(status_code=301, url=url)]
    response.url = redirect_url

    report = RedirectReport(response)
    
    self.assertEqual(report.status_code, 301)
    self.assertEqual(report.redirected_url, redirect_url)
    self.assertTrue(report.redirected_domain, 'xyz.net')

    
class TestWebsiteScraper(unittest.TestCase):
  
  def mock_check_domain_active(self):
    return True
  
  def setUp(self):
    self.url = "https://abc.com"
    self.scraper = WebsiteScraper(self.url)
    return

  @patch('requests.head')
  @patch.object(WebsiteScraper, 'check_domain_active', mock_check_domain_active)
  def test_response_200(self, mock_head):
    
    response = Mock()
    response.status_code = 200
    response.history = []
    response.url = self.url
    mock_head.return_value = response

    report = self.scraper.test_connectivity()
    
    self.assertTrue(report.is_domain_active)
    self.assertTrue(report.is_server_reachable)
    self.assertTrue(report.is_website_accessible)
    self.assertEqual(report.status_code, 200)
    self.assertFalse(report.error)
    
    
  @patch('requests.get')
  @patch('requests.head')
  @patch.object(WebsiteScraper, 'check_domain_active', mock_check_domain_active)
  def test_response_404(self, mock_head, mock_get):
    
    e =HTTPError()
    e.errno = 404
    e.strerror = 'Not Found'
    
    response = Mock()
    response.status_code = 404
    response.history = []
    response.url = self.url
    response.raise_for_status = Mock(side_effect=e)
    
    mock_head.return_value = response
    mock_get.return_value = response

    report = self.scraper.test_connectivity()
    
    self.assertTrue(report.is_domain_active)
    self.assertTrue(report.is_server_reachable)
    self.assertFalse(report.is_website_accessible)
    self.assertEqual(report.status_code, 404)
    self.assertTrue(report.error)
    
    
  @patch('requests.get')
  @patch('requests.head')
  @patch.object(WebsiteScraper, 'check_domain_active', mock_check_domain_active)
  def test_response_403(self, mock_head, mock_get):
    
    e =HTTPError()
    e.errno = 403
    e.strerror = 'Not Found'
    
    response = Mock()
    response.status_code = 403
    response.history = []
    response.url = self.url
    response.raise_for_status = Mock(side_effect=e)
    
    mock_head.return_value = response
    mock_get.return_value = response

    report = self.scraper.test_connectivity()
    
    self.assertTrue(report.is_domain_active)
    self.assertTrue(report.is_server_reachable)
    self.assertFalse(report.is_website_accessible)
    self.assertEqual(report.status_code, 403)
    self.assertTrue(report.error)
    
    
  @patch('requests.get')
  @patch('requests.head')
  @patch.object(WebsiteScraper, 'check_domain_active', mock_check_domain_active)
  def test_response_405(self, mock_head, mock_get):
    
    e =HTTPError()
    e.errno = 405
    e.strerror = 'Not Found'
    
    response = Mock()
    response.status_code = 405
    response.history = []
    response.url = self.url
    response.raise_for_status = Mock(side_effect=e)
    
    mock_head.return_value = response
    mock_get.return_value = response

    report = self.scraper.test_connectivity()
    
    self.assertTrue(report.is_domain_active)
    self.assertTrue(report.is_server_reachable)
    self.assertFalse(report.is_website_accessible)
    self.assertEqual(report.status_code, 405)
    self.assertTrue(report.error)
    
  
  @patch('scraper.RedirectReport') 
  @patch('requests.get')
  @patch('requests.head')
  @patch.object(WebsiteScraper, 'check_domain_active', mock_check_domain_active)
  def test_retry_on_405(self, mock_head, mock_get, MockRedirectReport):
    
    e =HTTPError()
    e.errno = 405
    e.strerror = 'Not Found'
    
    response = Mock()
    response.status_code = 405
    response.history = []
    response.url = self.url
    response.raise_for_status = Mock(side_effect=e)
    
    mock_head.return_value = response
    mock_get.return_value = response

    report = self.scraper.test_connectivity(abort_on_405=False)
    
    self.assertTrue(mock_get.called)
    self.assertFalse(report.is_website_accessible)
    
    mock_get.reset_mock()
    report = self.scraper.test_connectivity(abort_on_405=True)
    
    self.assertFalse(mock_get.called)
    self.assertFalse(report.is_website_accessible)

if __name__ == '__main__':
    unittest.main()
    