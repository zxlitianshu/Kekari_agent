package com.eriabank.houseinbox.ai.domain;

import java.util.List;

public class GigaProductDetailResponse {

    private boolean success;

    private List<GigaProductDetail> data;

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public List<GigaProductDetail> getData() {
        return data;
    }

    public void setData(List<GigaProductDetail> data) {
        this.data = data;
    }
}
