package com.eriabank.houseinbox.ai.service.impl;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import com.eriabank.houseinbox.ai.domain.GigaProductDetail;
import com.eriabank.houseinbox.ai.domain.GigaProductDetailResponse;
import com.eriabank.houseinbox.ai.service.IGigaApi;
import com.eriabank.houseinbox.common.util.ListUtil;
import com.eriabank.houseinbox.common.util.StringUtil;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import okhttp3.FormBody;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

@Service("gigaApi")
public class GigaApiImpl implements IGigaApi {

    private static final Logger log = LoggerFactory.getLogger(GigaApiImpl.class);

    private static final ObjectMapper mapper = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .configure(JsonParser.Feature.ALLOW_COMMENTS, true);

    private final OkHttpClient client = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build();

    private static final String TOKEN_URL = "https://api.gigacloudlogistics.com/api-auth-v1/oauth/token";

    private static final String PRODUCT_DETAIL_URL = "https://api.gigacloudlogistics.com/api-b2b-v1/product/detailInfo";

    private static final String REDIS_KEY_PREFIX = "giga_token:";

    private static final long BUFFER_SECONDS = 60; // 提前60秒刷新

    private static final Map<String, String> SITE_CLIENT_ID_MAP = new HashMap<>();

    static {
        SITE_CLIENT_ID_MAP.put("US", "32379916_USA_release");
        SITE_CLIENT_ID_MAP.put("DE", "83023006_GBR_release");
        SITE_CLIENT_ID_MAP.put("EU", "25828723_DEU_release");
//        SITE_CLIENT_ID_MAP.put("", "");
    }

    private static final Map<String, String> CLIENT_ID_SECRET_MAP = new HashMap<>();

    static {
        CLIENT_ID_SECRET_MAP.put("32379916_USA_release", "f7ef59281a0747bd8b628b7417a16701");
        CLIENT_ID_SECRET_MAP.put("83023006_GBR_release", "774c8a298add4a7bb3b30456058c5bdc");
        CLIENT_ID_SECRET_MAP.put("25828723_DEU_release", "a05e1de7e20442ddbd0455172330d715");
//        CLIENT_ID_SECRET_MAP.put("", "");
    }

    private final StringRedisTemplate redisTemplate;

    @Autowired
    public GigaApiImpl(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public String getToken(String site) {
        String clientId = SITE_CLIENT_ID_MAP.get(site);
        String clientSecret = CLIENT_ID_SECRET_MAP.get(clientId);
        if (StringUtil.isEmpty(clientId) || StringUtil.isEmpty(clientSecret)) {
            return null;
        }

        String redisKey = REDIS_KEY_PREFIX + clientId;
        // 从 Redis 获取缓存
        String cachedToken = redisTemplate.opsForValue().get(redisKey);
        if (cachedToken != null) {
            return cachedToken;
        }

        // 缓存失效，重新请求 token
        RequestBody requestBody = new FormBody.Builder()
                .add("grant_type", "client_credentials")
                .add("client_id", clientId)
                .add("client_secret", clientSecret)
                .build();

        Request request = new Request.Builder()
                .url(TOKEN_URL)
                .post(requestBody)
                .header("Content-Type", "application/x-www-form-urlencoded")
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                log.error("giga token response unsuccessful:" + response.toString());
                return null;
            }

            String responseBody = response.body().string();
            JsonNode json = mapper.readTree(responseBody);

            if (!json.has("access_token") || !json.has("expires_in")) {
                log.error("giga token response can`t find 'access_token' and 'expires_in' field:" + json.asText());
                return null;
            }

            String accessToken = json.get("access_token").asText();
            long expiresIn = json.get("expires_in").asLong(); // 单位：秒

            // 存入Redis，提前60秒过期
            long cacheSeconds = Math.max(0, expiresIn - BUFFER_SECONDS);
            redisTemplate.opsForValue().set(redisKey, accessToken, cacheSeconds, TimeUnit.SECONDS);

            return accessToken;
        } catch (Exception e) {
            log.error("request giga token failed:", e);
            return null;
        }

    }

    @Override
    public List<GigaProductDetail> getProductBySkus(String site, List<String> skuList) throws IOException {
        if (ListUtil.isEmpty(skuList)) {
            throw new IllegalArgumentException("skuList can`t be null!");
        }
        if (skuList.size() > 200) {
            throw new IllegalArgumentException("skuList size can`t exceed 200");
        }

        // 获取 access token
        String token = getToken(site);
        if (token == null) {
            throw new IllegalArgumentException("failed to obtain access token");
        }

        // 构造请求 JSON
        Map<String, Object> jsonMap = new HashMap<>();
        jsonMap.put("skus", skuList);
        String jsonBody = mapper.writeValueAsString(jsonMap);
        RequestBody body = RequestBody.create(MediaType.parse("application/json"), jsonBody);

        Request request = new Request.Builder()
                .url(PRODUCT_DETAIL_URL)
                .post(body)
                .header("Authorization", "Bearer " + token)
                .header("Content-Type", "application/json")
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Giga request product/detailInfo failed: " + response.code() + " - " + response.message());
            }

            String responseBody = response.body().string();
            GigaProductDetailResponse productResponse = mapper.readValue(responseBody, GigaProductDetailResponse.class);
            return productResponse.getData();
        }
    }

}
