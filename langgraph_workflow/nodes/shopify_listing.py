import requests
from config import SHOP, ACCESS_TOKEN

# --- Product data ---
product_input = {
    "title": "110*55\" Modern U-shaped Sectional Sofa with Waist Pillows,6-seat Upholstered Symmetrical Sofa Furniture,Sleeper Sofa Couch with Chaise Lounge for Living Room,Apartment,5 Color",
    "descriptionHtml": '''<div><img src="https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_8762ccd2277338f8d283079c8c61696d.png" alt="" style="width: 100%;display:block; margin-top:24px;"></div>
<div style="width:100%; margin-top:24px;">
<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Product Description:</div>
<div style="margin-top:12px;word-break: break-word;white-space:pre-line;line-height:18px;">This modern sectional sofa has a classic design that will never go out of style. The upholstery and sleek lines blend perfectly to create a harmonious appearance that can suit any decor style and enhance your space. Our sofa comes with four waist pillows, providing extra support and a touch of decorative charm to your living space.</div>
</div>
<div style="width:100%; margin-top:24px;">
<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;">Features</div>
<table style="width:100%; margin-top:12px;border: 1px solid #E5E5E5;border-bottom:0;" cellspacing="0">
<tbody>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Product Type</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Sofa</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Design</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Modular Sofa</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Products included</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Chaise,One Seat Sofa,armrest</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seating Capacity</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">6</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Upholstery Material</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">White Color: Chenille,Gray Color: Velvet</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Frame Material</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Solid + Manufactured Wood+Iron</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Leg Material</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Solid Wood</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seat Fill Material</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Foam; Pocket Spring</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Back Fill Material</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">PP cotton</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Removable Cushions</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Yes</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Removable Cushion Location</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seat,backrest</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Removable Cushion Cover</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Yes</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Reversible Cushions</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Yes</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Reversible Cushion Location</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seat,backrest</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Pillows Included</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Yes,4 included</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Product Care</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Lightly brush or vacuum frequently to remove dust and grime. Spot clean using a mild water-based solvent. Pre-test cleaning methods on a hidden surface. A professional cleaning service is recommended for an overall soiled condition.</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seat Style</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Multiple cushion seat</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Back Type</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Semi-Attached Pillows</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Supplier Intended and Approved Use</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Residential Use</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Country of Origin</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">China</td>
</tr>
</tbody>
</table>
</div>
<div style="width:100%; margin-top:24px;">
<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;">Product Dimensions</div>
<table style="width:100%; margin-top:12px;border: 1px solid #E5E5E5;border-bottom:0;" cellspacing="0">
<tbody>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Overall</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">110*55*33''(L*D*H)</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Back Height - Seat to Top of Back</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">16''</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Arm Height - Floor to Arm</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">22.8"</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Seat Height- Floor to Seat</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">19"</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Leg Height - Top to Bottom</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">3"</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Weight Capacity</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">330 lbs / seat</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Adult Assembly Required</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Yes</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Suggested # of People</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">2</td>
</tr>
<tr>
<td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Additional Tools Required</td>
<td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">Tools included</td>
</tr>
</tbody>
</table>
</div>
<div style="width:100%; margin-top:24px;">
<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Notice:</div>
<div style="margin-top:12px;word-break: break-word;white-space:pre-line;line-height:18px;">The packaging of the product package may be updated at any time, please refer to the actual product received.
All colors on our website are for reference only, actual product colors may vary a little bit, due to different colour settings of every screen device.
Please note: most of our sofas are hand-measured, therefore the dimensions are for reference only, and may marginally deviate.</div>
</div>
<div style="width:100%; margin-top:24px;">
<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Keep it looking its best:</div>
<div style="margin-top:12px;word-break: break-word;white-space:pre-line;line-height:18px;">c Blot spills immediately with a clean, absorbent white cloth.
c For indoor use only.
c Avoid direct sunlight.
c Do not leave newspaper or other printed material lying on surface.
c Dimensions of bench-made upholstery may vary slightly.
c Vacuum regularly.
c Spot clean using distilled water and water-based cleaning agents, foam or mild water-free cleaning solvents.
c Always test a small inconspicuous area first.</div>
</div>
''',
    "productType": "Sofas",
    "vendor": "Default Vendor",
    "status": "ACTIVE"
}

# --- Media (images) ---
media = [
    {"originalSource": url, "mediaContentType": "IMAGE"}
    for url in [
        
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/36bd6175b326e00a076b7fb2f2fb29f9.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=978b4d459fb1a461190275bde4098fba",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/52709288bfed5a382c3c13ef023b69d7.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=889495531649647022d2e02006e2aa54",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/28b7315191a1c8c66c4299c5b85e2224.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=218664f4212e059eed22b4d768583cbc",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/70b94b5c6b477351f53ca0fcb6bc500c.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=b2f977f62db496e818be2b4e40a1577b",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/0e50eb5b975cad3f8dbc3c8195b9a36b.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=04daa8a297a434ec1f31a5857f355816",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/6043278378f63cd84e98612c0abb77a4.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=e55ba6372ae01d031b205e000c986189",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/d04c4979a8622ee9d0eebff9602042a3.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=10a935f106ed3a77ecb13dc8178a9e18",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_8f86b1ed813fa813907f87b67c2e73ef.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=484900715c9321b977f9a8d330523779",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_b2542a12e0590f9918b83e2f1f4cac92.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=bce053a838edde1134da6e44054fda38",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_eaf7d612023584cbcbe5283de2cb961a.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=3bcce97be0754756955ee6842ed94ff1",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_b7f567af860656c71f117edcaf60e832.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=6fa893364cdaa69b0b24160a94f60a18",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_ec9bb59f9a2ef9238fc12d09b520454c.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=313103a2e4832222423d746b2a243348",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_20b2ad083743d68970931754c5238e31.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=425cf7335fc862bbbf4af554d0c4668d",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_bc6f61882f90e7668cfd4a640cbf5d2f.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=4bfe1f7c94c5af46f2e94625625d0d78",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_06825d770a3aee4bde2aaea0119bbdb5.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=0c4922c841ef010e9b5e008f39e57f58",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_be102956efc35b9eb4f72be960e25a80.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=bde1ddfdc608542e49efbbf4be277a4c",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_9cac2deae560849e2ea063f6f091e87e.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=f6f1374b45858c4c31305b2f23704d10",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_ac0abd28eb78d570affaf4ebbc62a164.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=f6c62fac65921cca2f59831249bb58ce",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/20230927_f1f2a27aefce5e337446c06bddd12d78.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=fc007bef22dea5107a84ac860d52d083",
        "https://b2bfiles1.gigab2b.cn/image/wkseller/3323/law_label/2025-04-21/GS008004AAA.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=4a6ac81b56599519bc63bd4690a6d320",
    ]
]

url = f"https://{SHOP}/admin/api/2025-04/graphql.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

# --- Step 1: Get Online Store publication ID ---
publications_query = """
query {
  publications(first: 10) {
    edges {
      node {
        id
        name
      }
    }
  }
}
"""

resp = requests.post(url, headers=headers, json={"query": publications_query})
result = resp.json()
print("Publications result:", result)

# Find the Online Store publication
publication_id = None
for edge in result["data"]["publications"]["edges"]:
    if "Online Store" in edge["node"]["name"]:
        publication_id = edge["node"]["id"]
        break

if not publication_id:
    raise Exception("Online Store publication ID not found!")
print(f"Online Store publication ID: {publication_id}")

# --- Step 2: Create Product ---
create_product_query = """
mutation productCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
  productCreate(input: $input, media: $media) {
    product { id title }
    userErrors { field message }
  }
}
"""
variables = {"input": product_input, "media": media}
resp = requests.post(url, headers=headers, json={"query": create_product_query, "variables": variables})
result = resp.json()
print("Product creation result:", result)
product_id = result["data"]["productCreate"]["product"]["id"]

# Step 2: Publish the product
print("\n--- Step 2: Publishing product ---")
publish_mutation = """
mutation publishProduct($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable {
      ... on Product {
        id
        title
        status
        publishedAt
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

publish_variables = {
    "id": product_id,
    "input": [{"publicationId": publication_id}]
}

publish_response = requests.post(url, headers=headers, json={"query": publish_mutation, "variables": publish_variables}).json()

if publish_response.get("errors"):
    print("Error publishing product:")
    for error in publish_response["errors"]:
        print(f"  - {error['message']}")
    exit(1)

publish_data = publish_response.get("data", {}).get("publishablePublish", {})
if publish_data.get("userErrors"):
    print("Error publishing product:")
    for error in publish_data["userErrors"]:
        print(f"  - {error['message']}")
    exit(1)

print("✅ Product published successfully!")
print(f"   Product ID: {product_id}")
print(f"   Published at: {publish_data.get('publishable', {}).get('publishedAt')}")

# Step 3: Get default location ID
print("\n--- Step 3: Getting default location ---")
locations_query = """
query {
  locations(first: 10) {
    edges {
      node {
        id
        name
      }
    }
  }
}
"""

locations_response = requests.post(url, headers=headers, json={"query": locations_query}).json()
if locations_response.get("errors"):
    print("Error getting locations:")
    for error in locations_response["errors"]:
        print(f"  - {error['message']}")
    exit(1)

locations_data = locations_response.get("data", {}).get("locations", {}).get("edges", [])
if not locations_data:
    print("❌ No locations found")
    exit(1)

# Use the first available location
location_id = locations_data[0]["node"]["id"]
print(f"   Using first location: {locations_data[0]['node']['name']} (ID: {location_id})")

# Step 4: Update the default variant with SKU, price, and inventory
print("\n--- Step 4: Updating default variant ---")
update_variant_mutation = """
mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!, $strategy: ProductVariantsBulkCreateStrategy!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: $strategy) {
    productVariants {
      id
      sku
      price
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""

update_variant_variables = {
    "productId": product_id,
    "variants": [
        {
            "price": "100.00",
            "inventoryItem": {"sku": "GS008004AAA"},
            "inventoryQuantities": [
                {
                    "availableQuantity": 100,
                    "locationId": location_id
                }
            ]
        }
    ],
    "strategy": "REMOVE_STANDALONE_VARIANT"
}

update_variant_response = requests.post(url, headers=headers, json={"query": update_variant_mutation, "variables": update_variant_variables}).json()

if update_variant_response.get("errors"):
    print("Error updating variant:")
    for error in update_variant_response["errors"]:
        print(f"  - {error['message']}")
    exit(1)

update_variant_data = update_variant_response.get("data", {}).get("productVariantsBulkCreate", {})
if update_variant_data.get("userErrors"):
    print("Error updating variant:")
    for error in update_variant_data["userErrors"]:
        print(f"  - {error['message']}")
    exit(1)

updated_variants = update_variant_data.get("productVariants", [])
if updated_variants:
    updated_variant = updated_variants[0]
    print("✅ Default variant updated successfully!")
    print(f"   SKU: {updated_variant.get('sku')}")
    print(f"   Price: ${updated_variant.get('price')}")
    inv = updated_variant.get('inventoryQuantities', [{}])[0]
    print(f"   Inventory: {inv.get('availableQuantity')}")
else:
    print("❌ No variants updated!")

# Step 5: Get the live product URL
print("\n--- Step 5: Getting live product URL ---")
get_product_query = """
query getProduct($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    onlineStoreUrl
  }
}
"""

product_response = requests.post(url, headers=headers, json={"query": get_product_query, "variables": {"id": product_id}}).json()
if product_response.get("errors"):
    print("Error getting product details:")
    for error in product_response["errors"]:
        print(f"  - {error['message']}")
    exit(1)

product_data = product_response.get("data", {}).get("product", {})
handle = product_data.get("handle")
online_store_url = product_data.get("onlineStoreUrl")

if online_store_url:
    live_url = online_store_url
else:
    live_url = f"https://{SHOP}/products/{handle}"

print(f"✅ Live product URL: {live_url}")

print("\n🎉 Product listing and publishing completed successfully!")
print(f"   Admin URL: https://{SHOP}/admin/products/{product_id.split('/')[-1]}")
print(f"   Live URL: {live_url}") 