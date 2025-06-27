package com.eriabank.houseinbox.ai.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

public class GigaProductAttribute {

    @JsonProperty("Main Color")
    private String mainColor;

    @JsonProperty("Scene")
    private String scene;

    @JsonProperty("Main Material")
    private String mainMaterial;

    public String getMainColor() {
        return mainColor;
    }

    public void setMainColor(String mainColor) {
        this.mainColor = mainColor;
    }

    public String getScene() {
        return scene;
    }

    public void setScene(String scene) {
        this.scene = scene;
    }

    public String getMainMaterial() {
        return mainMaterial;
    }

    public void setMainMaterial(String mainMaterial) {
        this.mainMaterial = mainMaterial;
    }
}
