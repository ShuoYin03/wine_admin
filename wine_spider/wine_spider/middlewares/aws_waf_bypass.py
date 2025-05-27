import logging
import random
import time
import json
import os
from typing import Optional, Dict, Any
from scrapy import signals
from scrapy_playwright.page import PageMethod

class AwsWafBypassMiddleware:
    """Middleware for bypassing AWS WAF protection."""
    
    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.retry_counts = {}
        self.max_retries = settings.getint('AWS_WAF_MAX_RETRIES', 5)
        self.min_delay = settings.getint('AWS_WAF_MIN_DELAY', 2000)
        self.max_delay = settings.getint('AWS_WAF_MAX_DELAY', 5000)
        
        self.stored_cookies = {}
        self.stored_tokens = {}
        
        self.enabled_spiders = settings.get('AWS_WAF_ENABLED_SPIDERS', [])
        
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def spider_opened(self, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            self.logger.info(f"WAF Bypass Middleware not enabled for {spider.name}")
            return
        
        self.logger.info("AWS WAF Bypass Middleware enabled for {spider.name}")
        
    def spider_closed(self, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return
            
        self.logger.info(f"AWS WAF Bypass Middleware closed for {spider.name}")
    
    def process_request(self, request, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return None
        
        if not request.meta.get('playwright', False):
            return None
            
        request.meta.update(self._get_playwright_meta(request.url))
        
        domain = self._get_domain(request.url)
        if domain in self.stored_cookies:
            if not 'playwright_context_args' in request.meta:
                request.meta['playwright_context_args'] = {}
                
            request.meta['playwright_context_args']['storage_state'] = {
                'cookies': self.stored_cookies[domain]
            }
            
        return None
    
    def process_response(self, request, response, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return response
            
        if not response.meta.get('playwright_page'):
            return response
            
        url = request.url
        try:
            if "challenge-container" in response.text or "awswaf" in response.text:
                self.logger.info(f"Detected WAF challenge page at {url}")
                
                retry_count = self.retry_counts.get(url, 0) + 1
                self.retry_counts[url] = retry_count
                
                if retry_count <= self.max_retries:
                    self.logger.info(f"Scheduling retry {retry_count}/{self.max_retries} for {url}")
                    
                    retry_delay = 10 * (2 ** (retry_count - 1))
                    time.sleep(retry_delay)
                    
                    self._handle_waf_page(response, url)
                    
                    new_request = request.replace(dont_filter=True)
                    return new_request
                else:
                    self.logger.error(f"Maximum retry attempts reached for {url}")
                    return response
            else:
                if url in self.retry_counts:
                    self.retry_counts.pop(url)
        
        except Exception as e:
            if type(response.body) == bytes:
                pass
                
        return response
    
    async def _handle_waf_page(self, response, url):
        try:
            page = response.meta["playwright_page"]
            
            await page.wait_for_timeout(5000)
            
            tokens = await page.evaluate("""() => {
                const tokens = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key.includes('waf') || key.includes('token') || key.includes('challenge')) {
                        tokens[key] = localStorage.getItem(key);
                    }
                }
                return tokens;
            }""")
            
            if tokens:
                domain = self._get_domain(url)
                self.stored_tokens[domain] = tokens
                self.logger.info(f"Extracted WAF tokens from {url}")
            
        except Exception as e:
            self.logger.error(f"Error handling WAF page: {e}")
    
    def _get_playwright_meta(self, url=None) -> Dict[str, Any]:
        random_timeout = random.randint(self.min_delay, self.max_delay)
        
        page_coroutines = [
            PageMethod("wait_for_timeout", random_timeout),
            
            PageMethod("evaluate", """() => {
                const cookieButtons = Array.from(document.querySelectorAll('button')).filter(el => 
                    el.textContent.toLowerCase().includes('accept') || 
                    el.textContent.toLowerCase().includes('cookie')
                );
                if (cookieButtons.length > 0) cookieButtons[0].click();
            }"""),
            
            PageMethod("evaluate", """() => {
                const randomMove = () => {
                    const event = new MouseEvent('mousemove', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': Math.floor(Math.random() * window.innerWidth),
                        'clientY': Math.floor(Math.random() * window.innerHeight)
                    });
                    document.dispatchEvent(event);
                };
                
                for (let i = 0; i < 5; i++) {
                    setTimeout(randomMove, i * 300);
                }
            }"""),
            
            PageMethod("wait_for_selector", "body", {"state": "visible", "timeout": 30000}),
            PageMethod("wait_for_timeout", random.randint(1000, 2000)),
        ]
        
        if url:
            domain = self._get_domain(url)
            if domain in self.stored_tokens:
                token_script = self._build_token_script(self.stored_tokens[domain])
                if token_script:
                    page_coroutines.insert(0, PageMethod("evaluate", token_script))
        
        meta = {
            "playwright_page_coroutines": page_coroutines
        }
        
        return meta
    
    def _build_token_script(self, tokens: Dict[str, str]) -> Optional[str]:
        if not tokens:
            return None
            
        script_parts = ["(() => {"]
        
        for key, value in tokens.items():
            script_parts.append(f"  try {{ localStorage.setItem('{key}', '{value}'); }} catch (e) {{}}") 
            
        script_parts.append("  return true;")
        script_parts.append("})();")
        
        return "\n".join(script_parts)
    
    def _get_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc