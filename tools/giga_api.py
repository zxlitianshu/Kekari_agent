import requests
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GigaProductAttribute:
    main_color: Optional[str] = None
    scene: Optional[str] = None
    main_material: Optional[str] = None

@dataclass
class GigaProductComboInfo:
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    weightKg: Optional[float] = None
    lengthCm: Optional[float] = None
    widthCm: Optional[float] = None
    heightCm: Optional[float] = None
    qty: Optional[int] = None
    sku: Optional[str] = None

@dataclass
class GigaProductDetail:
    sku: str
    name: Optional[str] = None
    description: Optional[str] = None
    characteristics: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    category: Optional[str] = None
    category_code: Optional[str] = None
    weight: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    attributes: Optional[GigaProductAttribute] = None
    combo_info: Optional[List[GigaProductComboInfo]] = None
    main_image_url: Optional[str] = None
    # Add more fields as needed

class GigaApiClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
        
        # API endpoints
        self.TOKEN_URL = "https://api.gigacloudlogistics.com/api-auth-v1/oauth/token"
        self.PRODUCT_DETAIL_URL = "https://api.gigacloudlogistics.com/api-b2b-v1/product/detailInfo"
        
        # Site to client ID mapping
        self.SITE_CLIENT_ID_MAP = {
            "US": "32379916_USA_release",
            "DE": "83023006_GBR_release", 
            "EU": "25828723_DEU_release"
        }
        
        # Client ID to secret mapping
        self.CLIENT_ID_SECRET_MAP = {
            "32379916_USA_release": "f7ef59281a0747bd8b628b7417a16701",
            "83023006_GBR_release": "774c8a298add4a7bb3b30456058c5bdc",
            "25828723_DEU_release": "a05e1de7e20442ddbd0455172330d715"
        }
        
        # Token cache
        self._token_cache = {}
        self._token_expiry = {}
    
    def _get_token(self, site: str) -> Optional[str]:
        """Get OAuth token for the given site"""
        client_id = self.SITE_CLIENT_ID_MAP.get(site)
        if not client_id:
            logger.error(f"Unknown site: {site}")
            return None
            
        client_secret = self.CLIENT_ID_SECRET_MAP.get(client_id)
        if not client_secret:
            logger.error(f"No secret found for client ID: {client_id}")
            return None
        
        # Check if we have a valid cached token
        if site in self._token_cache and site in self._token_expiry:
            if time.time() < self._token_expiry[site]:
                logger.info(f"Using cached token for site: {site}")
                return self._token_cache[site]
        
        # Request new token
        logger.info(f"Requesting new token for site: {site}")
        token_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = self.session.post(self.TOKEN_URL, data=token_data, headers=headers)
            response.raise_for_status()
            
            token_response = response.json()
            access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 3600)
            
            if not access_token:
                logger.error("No access_token in response")
                return None
            
            # Cache token with 60 second buffer
            self._token_cache[site] = access_token
            self._token_expiry[site] = time.time() + expires_in - 60
            
            logger.info(f"Token obtained and cached for site: {site}")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to get token for site {site}: {e}")
            return None
    
    def get_products_by_skus(self, site: str, sku_list: List[str]) -> List[GigaProductDetail]:
        """Get product details by SKU list"""
        if not sku_list:
            raise ValueError("sku_list cannot be empty")
        
        if len(sku_list) > 200:
            raise ValueError("sku_list size cannot exceed 200")
        
        # Get token
        token = self._get_token(site)
        if not token:
            raise ValueError(f"Failed to obtain access token for site: {site}")
        
        # Prepare request
        payload = {"skus": sku_list}
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Requesting {len(sku_list)} products from Giga API")
        
        try:
            response = self.session.post(
                self.PRODUCT_DETAIL_URL, 
                json=payload, 
                headers=headers
            )
            
            # Log response details for debugging
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            # Check if response has content
            if not response.content:
                logger.error("Empty response content")
                return []
            
            # Log response content for debugging
            logger.info(f"Response content: {response.text[:500]}...")
            
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success"):
                logger.error(f"API returned success=false: {data}")
                return []
            
            products_data = data.get("data", [])
            products = []
            
            for product_data in products_data:
                # Parse attributes - handle null values
                attributes = None
                if "attributes" in product_data and product_data["attributes"] is not None:
                    attr_data = product_data["attributes"]
                    attributes = GigaProductAttribute(
                        main_color=attr_data.get("Main Color"),
                        scene=attr_data.get("Scene"),
                        main_material=attr_data.get("Main Material")
                    )
                
                # Parse combo info - handle null values
                combo_info = None
                if "comboInfo" in product_data and product_data["comboInfo"] is not None:
                    combo_info = [
                        GigaProductComboInfo(**combo) 
                        for combo in product_data["comboInfo"]
                    ]
                
                # Create product detail
                product = GigaProductDetail(
                    sku=product_data.get("sku", ""),
                    name=product_data.get("name"),
                    description=product_data.get("description"),
                    characteristics=product_data.get("characteristics"),
                    image_urls=product_data.get("imageUrls"),
                    category=product_data.get("category"),
                    category_code=product_data.get("categoryCode"),
                    weight=product_data.get("weight"),
                    length=product_data.get("length"),
                    width=product_data.get("width"),
                    height=product_data.get("height"),
                    weight_kg=product_data.get("weightKg"),
                    length_cm=product_data.get("lengthCm"),
                    attributes=attributes,
                    combo_info=combo_info,
                    main_image_url=product_data.get("mainImageUrl")
                )
                products.append(product)
            
            logger.info(f"Successfully retrieved {len(products)} products")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            raise 