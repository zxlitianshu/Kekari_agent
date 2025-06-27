package com.eriabank.houseinbox.ai.service;

import java.io.IOException;
import java.util.List;

import com.eriabank.houseinbox.ai.domain.GigaProductDetail;

public interface IGigaApi {

    List<GigaProductDetail> getProductBySkus(String site, List<String> skuList) throws IOException;

}
