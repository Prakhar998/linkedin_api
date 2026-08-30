import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

app.config['JSON_SORT_KEYS'] = False
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 3600})

limiter = Limiter(app=app, key_func=get_remote_address, storage_uri="memory://")

LINKEDIN_API_BASE = "https://www.linkedin.com/voyager/api"
LINKEDIN_REST_API = "https://www.linkedin.com/rest/graphql"

def create_session(csrf_token: str = None, li_at_cookie: str = None):
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/vnd.linkedin.normalized+json+2.1',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })

    if csrf_token:
        session.headers['X-CSRF-Token'] = csrf_token
        session.headers['X-RestLi-Protocol-Version'] = '2.0.0'

    if li_at_cookie:
        session.cookies.set('li_at', li_at_cookie, domain='www.linkedin.com')

    return session


class LinkedInProfileScraper:
    def __init__(self, csrf_token: str, li_at_cookie: str):
        self.session = create_session(csrf_token, li_at_cookie)
        self.csrf_token = csrf_token
        self.li_at_cookie = li_at_cookie
        self.debug_info = {}

    def extract_urn_from_url(self, url: str) -> Optional[str]:
        try:
            if 'linkedin.com/in/' in url.lower():
                return url.split('/in/')[-1].split('/?')[0].split('?')[0].strip('/')
            elif 'linkedin.com/company/' in url.lower():
                return url.split('/company/')[-1].split('/?')[0].split('?')[0].strip('/')
            return None
        except Exception as e:
            logger.error(f"Error extracting URN: {e}")
            return None

    def validate_credentials(self) -> Tuple[bool, str]:
        """Check if the stored credentials are still valid."""
        try:
            url = f"{LINKEDIN_API_BASE}/me"
            response = self.session.get(url, timeout=10)
            logger.debug(f"Credential validation response: {response.status_code}")

            if response.status_code == 200:
                return True, "Credentials valid"
            elif response.status_code == 401:
                return False, "Credentials expired (401)"
            elif response.status_code == 403:
                return False, "Access forbidden (403) - IP may be blocked"
            else:
                return False, f"Unexpected status: {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Timeout validating credentials"
        except Exception as e:
            return False, f"Error validating credentials: {str(e)}"

    def get_profile_by_public_id(self, public_id: str) -> Tuple[Optional[Dict], Dict]:
        """Try multiple endpoints to fetch profile data."""
        self.debug_info = {'public_id': public_id, 'attempts': []}

        # Strategy 1: meProfessionalProfile endpoint
        url = f"{LINKEDIN_API_BASE}/meProfessionalProfile?q=memberIdentity&memberIdentity={public_id}"
        logger.debug(f"Attempting endpoint 1: {url}")
        try:
            response = self.session.get(url, timeout=10)
            self.debug_info['attempts'].append({
                'endpoint': 'meProfessionalProfile',
                'status': response.status_code,
                'success': response.status_code == 200
            })
            logger.debug(f"Strategy 1 response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data and data.get('data'):
                    return data, self.debug_info
        except Exception as e:
            logger.warning(f"Strategy 1 failed: {str(e)}")
            self.debug_info['attempts'].append({
                'endpoint': 'meProfessionalProfile',
                'error': str(e)
            })

        # Strategy 2: identityDashProfilesByMemberId
        url = f"{LINKEDIN_API_BASE}/identityDashProfilesByMemberId?q=memberIdentity&memberIdentity={public_id}"
        logger.debug(f"Attempting endpoint 2: {url}")
        try:
            response = self.session.get(url, timeout=10)
            self.debug_info['attempts'].append({
                'endpoint': 'identityDashProfilesByMemberId',
                'status': response.status_code,
                'success': response.status_code == 200
            })
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data, self.debug_info
        except Exception as e:
            logger.warning(f"Strategy 2 failed: {str(e)}")
            self.debug_info['attempts'].append({
                'endpoint': 'identityDashProfilesByMemberId',
                'error': str(e)
            })

        # Strategy 3: Simple voyager profile call
        url = f"{LINKEDIN_API_BASE}/profilesByPublicIdentifier?q=publicIdentifiers&publicIdentifiers={public_id}"
        logger.debug(f"Attempting endpoint 3: {url}")
        try:
            response = self.session.get(url, timeout=10)
            self.debug_info['attempts'].append({
                'endpoint': 'profilesByPublicIdentifier',
                'status': response.status_code,
                'success': response.status_code == 200
            })
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data, self.debug_info
        except Exception as e:
            logger.warning(f"Strategy 3 failed: {str(e)}")
            self.debug_info['attempts'].append({
                'endpoint': 'profilesByPublicIdentifier',
                'error': str(e)
            })

        logger.error(f"All strategies failed for public_id: {public_id}")
        return None, self.debug_info
    
    def parse_profile_response(self, profile_data: Dict) -> Dict[str, Any]:
        if not profile_data:
            return {}
        
        profile_info = profile_data.get('data', {}).get('profile', {}) or profile_data
        
        return {
            'id': self._extract_nested(profile_info, ['entityUrn']),
            'firstName': self._extract_nested(profile_info, ['firstName']),
            'lastName': self._extract_nested(profile_info, ['lastName']),
            'headline': self._extract_nested(profile_info, ['headline']),
            'location': self._extract_location(profile_info),
            'about': self._extract_nested(profile_info, ['about']),
            'profileImage': self._extract_profile_image(profile_info),
            'experience': self._extract_experience(profile_info),
            'education': self._extract_education(profile_info),
            'skills': self._extract_skills(profile_info),
            'certifications': self._extract_certifications(profile_info),
            'languages': self._extract_languages(profile_info),
        }
    
    def _extract_nested(self, data: Dict, keys: list, default=None):
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
        return current or default
    
    def _extract_location(self, profile_data: Dict) -> Optional[Dict]:
        location = self._extract_nested(profile_data, ['location'])
        return {'name': location.get('name'), 'country': location.get('country')} if location else None
    
    def _extract_profile_image(self, profile_data: Dict) -> Optional[str]:
        return (
            self._extract_nested(profile_data, ['profileImage', 'url']) or
            self._extract_nested(profile_data, ['profilePicture', 'url']) or
            self._extract_nested(profile_data, ['picture', 'url'])
        )
    
    def _extract_experience(self, profile_data: Dict) -> list:
        experiences = []
        exp_data = (
            self._extract_nested(profile_data, ['experience', 'edges']) or
            self._extract_nested(profile_data, ['experience']) or
            []
        )
        
        for item in (exp_data if isinstance(exp_data, list) else []):
            if isinstance(item, dict):
                node = item.get('node', item)
                exp = {
                    'title': node.get('title'),
                    'company': node.get('company'),
                    'location': node.get('location'),
                    'startDate': node.get('startDate'),
                    'endDate': node.get('endDate'),
                    'duration': node.get('duration'),
                    'description': node.get('description'),
                    'isCurrent': node.get('isCurrent', False)
                }
                if exp.get('company') or exp.get('title'):
                    experiences.append(exp)
        
        return experiences
    
    def _extract_education(self, profile_data: Dict) -> list:
        education = []
        edu_data = (
            self._extract_nested(profile_data, ['education', 'edges']) or
            self._extract_nested(profile_data, ['education']) or
            []
        )
        
        for item in (edu_data if isinstance(edu_data, list) else []):
            if isinstance(item, dict):
                node = item.get('node', item)
                edu = {
                    'schoolName': node.get('schoolName'),
                    'degree': node.get('degree'),
                    'fieldOfStudy': node.get('fieldOfStudy'),
                    'startDate': node.get('startDate'),
                    'endDate': node.get('endDate')
                }
                if edu.get('schoolName'):
                    education.append(edu)
        
        return education
    
    def _extract_skills(self, profile_data: Dict) -> list:
        skills = []
        skills_data = (
            self._extract_nested(profile_data, ['skills', 'edges']) or
            self._extract_nested(profile_data, ['skills']) or
            []
        )
        
        for item in (skills_data if isinstance(skills_data, list) else []):
            if isinstance(item, dict):
                node = item.get('node', item)
                skill = {'name': node.get('name'), 'endorsements': node.get('endorsements', 0)}
                if skill.get('name'):
                    skills.append(skill)
        
        return skills
    
    def _extract_certifications(self, profile_data: Dict) -> list:
        certs = []
        cert_data = (
            self._extract_nested(profile_data, ['certifications', 'edges']) or
            self._extract_nested(profile_data, ['certifications']) or
            []
        )
        
        for item in (cert_data if isinstance(cert_data, list) else []):
            if isinstance(item, dict):
                node = item.get('node', item)
                cert = {
                    'name': node.get('name'),
                    'issuer': node.get('issuer'),
                    'issueDate': node.get('issueDate'),
                    'expirationDate': node.get('expirationDate'),
                    'credentialUrl': node.get('credentialUrl')
                }
                if cert.get('name'):
                    certs.append(cert)
        
        return certs
    
    def _extract_languages(self, profile_data: Dict) -> list:
        langs = []
        lang_data = (
            self._extract_nested(profile_data, ['languages', 'edges']) or
            self._extract_nested(profile_data, ['languages']) or
            []
        )
        
        for item in (lang_data if isinstance(lang_data, list) else []):
            if isinstance(item, dict):
                node = item.get('node', item)
                lang = {'name': node.get('name'), 'proficiency': node.get('proficiency')}
                if lang.get('name'):
                    langs.append(lang)
        
        return langs


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    }), 200


@app.route('/api/v1/validate', methods=['GET'])
@limiter.limit("30 per minute")
def validate_credentials():
    """Check if the stored credentials are still valid."""
    try:
        csrf_token = os.getenv('LINKEDIN_CSRF_TOKEN', '')
        li_at_cookie = os.getenv('LINKEDIN_LI_AT_COOKIE', '')

        if not csrf_token or not li_at_cookie:
            return jsonify({
                'valid': False,
                'reason': 'Credentials not configured',
                'timestamp': datetime.utcnow().isoformat()
            }), 503

        scraper = LinkedInProfileScraper(csrf_token, li_at_cookie)
        is_valid, message = scraper.validate_credentials()

        return jsonify({
            'valid': is_valid,
            'reason': message,
            'timestamp': datetime.utcnow().isoformat(),
            'hint': 'Run python3 extract_credentials.py to update credentials' if not is_valid else None
        }), 200

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'valid': False,
            'reason': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/profile', methods=['GET'])
@limiter.limit("10 per minute")
@cache.cached(timeout=3600, query_string=True)
def get_profile():
    try:
        profile_url = request.args.get('url', '').strip()
        include_raw = request.args.get('include_raw', 'false').lower() == 'true'
        include_debug = request.args.get('debug', 'false').lower() == 'true'

        if not profile_url:
            return jsonify({'error': 'Missing required parameter: url'}), 400

        if 'linkedin.com' not in profile_url.lower():
            return jsonify({'error': 'Invalid LinkedIn URL'}), 400

        csrf_token = os.getenv('LINKEDIN_CSRF_TOKEN', '')
        li_at_cookie = os.getenv('LINKEDIN_LI_AT_COOKIE', '')

        if not csrf_token or not li_at_cookie:
            return jsonify({
                'error': 'API not configured - credentials missing',
                'hint': 'Set LINKEDIN_CSRF_TOKEN and LINKEDIN_LI_AT_COOKIE environment variables'
            }), 503

        scraper = LinkedInProfileScraper(csrf_token, li_at_cookie)

        # Validate credentials first
        is_valid, validation_msg = scraper.validate_credentials()
        if not is_valid:
            return jsonify({
                'error': 'Invalid or expired credentials',
                'reason': validation_msg,
                'hint': 'Run python3 extract_credentials.py to get fresh credentials',
                'status': 'credentials_expired'
            }), 401

        public_id = scraper.extract_urn_from_url(profile_url)

        if not public_id:
            return jsonify({'error': 'Could not extract profile ID from URL'}), 400

        raw_data, debug_info = scraper.get_profile_by_public_id(public_id)
        if not raw_data:
            response = {
                'error': 'Failed to fetch profile',
                'public_id': public_id,
                'profileUrl': profile_url,
                'hint': 'Profile may be private or LinkedIn API endpoints may have changed',
                'status': 'profile_not_found'
            }
            if include_debug:
                response['debug'] = debug_info
            return jsonify(response), 404

        profile_data = scraper.parse_profile_response(raw_data)

        response = {
            'success': True,
            'data': profile_data,
            'metadata': {
                'fetchedAt': datetime.utcnow().isoformat(),
                'profileUrl': profile_url,
                'publicId': public_id,
                'cached': False
            }
        }

        if include_raw:
            response['raw'] = raw_data
        if include_debug:
            response['debug'] = debug_info

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e) if os.getenv('FLASK_ENV') == 'development' else None
        }), 500


@app.route('/api/v1/profile/batch', methods=['POST'])
@limiter.limit("5 per minute")
def get_profiles_batch():
    try:
        data = request.get_json()

        if not data or 'urls' not in data:
            return jsonify({'error': 'Missing required field: urls'}), 400

        urls = data.get('urls', [])
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({'error': 'urls must be a non-empty array'}), 400

        if len(urls) > 10:
            return jsonify({'error': 'Maximum 10 profiles per batch'}), 400

        csrf_token = os.getenv('LINKEDIN_CSRF_TOKEN', '')
        li_at_cookie = os.getenv('LINKEDIN_LI_AT_COOKIE', '')

        if not csrf_token or not li_at_cookie:
            return jsonify({'error': 'API not configured'}), 503

        scraper = LinkedInProfileScraper(csrf_token, li_at_cookie)

        # Validate credentials first
        is_valid, validation_msg = scraper.validate_credentials()
        if not is_valid:
            return jsonify({
                'error': 'Invalid or expired credentials',
                'reason': validation_msg,
                'hint': 'Run python3 extract_credentials.py to get fresh credentials'
            }), 401

        results = []
        for url in urls:
            try:
                public_id = scraper.extract_urn_from_url(url)
                if public_id:
                    raw_data, _ = scraper.get_profile_by_public_id(public_id)
                    if raw_data:
                        profile_data = scraper.parse_profile_response(raw_data)
                        results.append({'url': url, 'success': True, 'data': profile_data})
                    else:
                        results.append({'url': url, 'success': False, 'error': 'Profile not found'})
                else:
                    results.append({'url': url, 'success': False, 'error': 'Could not extract profile ID'})
            except Exception as e:
                results.append({'url': url, 'success': False, 'error': str(e)})

        return jsonify({
            'success': True,
            'data': results,
            'metadata': {
                'totalRequested': len(urls),
                'successfulCount': sum(1 for r in results if r.get('success')),
                'fetchedAt': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"Batch error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/v1/docs', methods=['GET'])
def get_docs():
    return jsonify({
        'name': 'LinkedIn Profile API',
        'version': '2.0.0',
        'endpoints': {
            'GET /health': 'Health check',
            'GET /api/v1/validate': 'Validate credentials (returns {valid: bool, reason: str})',
            'GET /api/v1/profile': 'Get single profile (param: url, debug=true for endpoint debug info)',
            'POST /api/v1/profile/batch': 'Get multiple profiles (body: {urls: [...]})',
            'GET /api/v1/docs': 'API documentation'
        },
        'features': {
            'multiple_endpoints': 'Tries 3 different LinkedIn API endpoints for better success rate',
            'credential_validation': 'Auto-validates credentials before each request',
            'debug_mode': 'Add ?debug=true to profile endpoint for endpoint attempt details',
            'error_hints': 'Detailed error messages with actionable hints'
        }
    }), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=debug, use_reloader=False)