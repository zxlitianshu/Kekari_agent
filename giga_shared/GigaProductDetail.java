package com.eriabank.houseinbox.ai.domain;

import java.math.BigDecimal;
import java.util.List;

public class GigaProductDetail {
    private String sku;
    private String mpn;
    private String weightUnit;
    private String lengthUnit;
    private BigDecimal weight;
    private BigDecimal length;
    private BigDecimal width;
    private BigDecimal height;
    private BigDecimal weightKg;
    private BigDecimal lengthCm;
    private String name;
    private String description;
    private List<String> characteristics;
    private List<String> imageUrls;
    private String categoryCode;
    private String category;
    private Boolean comboFlag;
    private Boolean overSizeFlag;
    private Boolean partFlag;
    private String upc;
    private String customized;
    private String placeOfOrigin;
    private String lithiumBatteryContained;
    private BigDecimal assembledLength;
    private BigDecimal assembledWidth;
    private BigDecimal assembledHeight;
    private BigDecimal assembledWeight;
    private List<String> customList;
    private List<String> associateProductList;
    private List<String> certificationList;
    private List<String> fileUrls;
    private List<String> videoUrls;
    private GigaProductAttribute attributes;
    private String whiteLabel;
    private List<GigaProductComboInfo> comboInfo;
    private String firstAvailableDate;
    private Object sellerInfo;
    private Boolean toBePublished;
    private List<Object> unAvailablePlatform;
    private String mainImageUrl;

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public String getMpn() {
        return mpn;
    }

    public void setMpn(String mpn) {
        this.mpn = mpn;
    }

    public String getWeightUnit() {
        return weightUnit;
    }

    public void setWeightUnit(String weightUnit) {
        this.weightUnit = weightUnit;
    }

    public String getLengthUnit() {
        return lengthUnit;
    }

    public void setLengthUnit(String lengthUnit) {
        this.lengthUnit = lengthUnit;
    }

    public BigDecimal getWeight() {
        return weight;
    }

    public void setWeight(BigDecimal weight) {
        this.weight = weight;
    }

    public BigDecimal getLength() {
        return length;
    }

    public void setLength(BigDecimal length) {
        this.length = length;
    }

    public BigDecimal getWidth() {
        return width;
    }

    public void setWidth(BigDecimal width) {
        this.width = width;
    }

    public BigDecimal getHeight() {
        return height;
    }

    public void setHeight(BigDecimal height) {
        this.height = height;
    }

    public BigDecimal getWeightKg() {
        return weightKg;
    }

    public void setWeightKg(BigDecimal weightKg) {
        this.weightKg = weightKg;
    }

    public BigDecimal getLengthCm() {
        return lengthCm;
    }

    public void setLengthCm(BigDecimal lengthCm) {
        this.lengthCm = lengthCm;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public List<String> getCharacteristics() {
        return characteristics;
    }

    public void setCharacteristics(List<String> characteristics) {
        this.characteristics = characteristics;
    }

    public List<String> getImageUrls() {
        return imageUrls;
    }

    public void setImageUrls(List<String> imageUrls) {
        this.imageUrls = imageUrls;
    }

    public String getCategoryCode() {
        return categoryCode;
    }

    public void setCategoryCode(String categoryCode) {
        this.categoryCode = categoryCode;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public Boolean getComboFlag() {
        return comboFlag;
    }

    public void setComboFlag(Boolean comboFlag) {
        this.comboFlag = comboFlag;
    }

    public Boolean getOverSizeFlag() {
        return overSizeFlag;
    }

    public void setOverSizeFlag(Boolean overSizeFlag) {
        this.overSizeFlag = overSizeFlag;
    }

    public Boolean getPartFlag() {
        return partFlag;
    }

    public void setPartFlag(Boolean partFlag) {
        this.partFlag = partFlag;
    }

    public String getUpc() {
        return upc;
    }

    public void setUpc(String upc) {
        this.upc = upc;
    }

    public String getCustomized() {
        return customized;
    }

    public void setCustomized(String customized) {
        this.customized = customized;
    }

    public String getPlaceOfOrigin() {
        return placeOfOrigin;
    }

    public void setPlaceOfOrigin(String placeOfOrigin) {
        this.placeOfOrigin = placeOfOrigin;
    }

    public String getLithiumBatteryContained() {
        return lithiumBatteryContained;
    }

    public void setLithiumBatteryContained(String lithiumBatteryContained) {
        this.lithiumBatteryContained = lithiumBatteryContained;
    }

    public BigDecimal getAssembledLength() {
        return assembledLength;
    }

    public void setAssembledLength(BigDecimal assembledLength) {
        this.assembledLength = assembledLength;
    }

    public BigDecimal getAssembledWidth() {
        return assembledWidth;
    }

    public void setAssembledWidth(BigDecimal assembledWidth) {
        this.assembledWidth = assembledWidth;
    }

    public BigDecimal getAssembledHeight() {
        return assembledHeight;
    }

    public void setAssembledHeight(BigDecimal assembledHeight) {
        this.assembledHeight = assembledHeight;
    }

    public BigDecimal getAssembledWeight() {
        return assembledWeight;
    }

    public void setAssembledWeight(BigDecimal assembledWeight) {
        this.assembledWeight = assembledWeight;
    }

    public List<String> getCustomList() {
        return customList;
    }

    public void setCustomList(List<String> customList) {
        this.customList = customList;
    }

    public List<String> getAssociateProductList() {
        return associateProductList;
    }

    public void setAssociateProductList(List<String> associateProductList) {
        this.associateProductList = associateProductList;
    }

    public List<String> getCertificationList() {
        return certificationList;
    }

    public void setCertificationList(List<String> certificationList) {
        this.certificationList = certificationList;
    }

    public List<String> getFileUrls() {
        return fileUrls;
    }

    public void setFileUrls(List<String> fileUrls) {
        this.fileUrls = fileUrls;
    }

    public List<String> getVideoUrls() {
        return videoUrls;
    }

    public void setVideoUrls(List<String> videoUrls) {
        this.videoUrls = videoUrls;
    }

    public GigaProductAttribute getAttributes() {
        return attributes;
    }

    public void setAttributes(GigaProductAttribute attributes) {
        this.attributes = attributes;
    }

    public String getWhiteLabel() {
        return whiteLabel;
    }

    public void setWhiteLabel(String whiteLabel) {
        this.whiteLabel = whiteLabel;
    }

    public List<GigaProductComboInfo> getComboInfo() {
        return comboInfo;
    }

    public void setComboInfo(List<GigaProductComboInfo> comboInfo) {
        this.comboInfo = comboInfo;
    }

    public String getFirstAvailableDate() {
        return firstAvailableDate;
    }

    public void setFirstAvailableDate(String firstAvailableDate) {
        this.firstAvailableDate = firstAvailableDate;
    }

    public Object getSellerInfo() {
        return sellerInfo;
    }

    public void setSellerInfo(Object sellerInfo) {
        this.sellerInfo = sellerInfo;
    }

    public Boolean getToBePublished() {
        return toBePublished;
    }

    public void setToBePublished(Boolean toBePublished) {
        this.toBePublished = toBePublished;
    }

    public List<Object> getUnAvailablePlatform() {
        return unAvailablePlatform;
    }

    public void setUnAvailablePlatform(List<Object> unAvailablePlatform) {
        this.unAvailablePlatform = unAvailablePlatform;
    }

    public String getMainImageUrl() {
        return mainImageUrl;
    }

    public void setMainImageUrl(String mainImageUrl) {
        this.mainImageUrl = mainImageUrl;
    }
}
