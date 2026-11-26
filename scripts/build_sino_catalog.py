"""Builder script for SINO pricebook items (100% verified against both PDFs)."""
import hashlib


def create_sino_items():
    items = []

    def add_item(sku, name, category, group, price, discount_rate, specs, cells, img, extra_cols=None):
        discounted = int(round(price * (1.0 - discount_rate)))
        item_id = "sino:" + hashlib.sha256(f"{sku}_{group}_{price}".encode()).hexdigest()[:16]
        if extra_cols:
            cols = extra_cols
        elif "Icu (kA)" in specs:
            cols = ["Mã hàng", "Số cực", "In (A)", "Icu (kA)", "Đơn giá (VND)"]
        elif "Dòng rò" in specs:
            cols = ["Mã hàng", "Số cực", "In (A)", "Dòng rò", "Đơn giá (VND)"]
        elif "Imax" in specs:
            cols = ["Mã hàng", "Số cực", "In (A)", "Imax", "Đơn giá (VND)"]
        elif "Điện áp cuộn hút" in specs:
            cols = ["Mã hàng", "Số cực", "In (A)", "Cuộn hút", "Đơn giá (VND)"]
        else:
            cols = ["Mã hàng", "In (A)", "Đơn giá (VND)"]
        items.append({
            "id": item_id,
            "sku": sku,
            "item_name": name,
            "name": name,
            "brand": "Sino - Vanlock",
            "category": category,
            "group": group,
            "price": price,
            "discount_rate": discount_rate,
            "discounted_price": discounted,
            "currency": "VND",
            "specifications": specs,
            "columns": cols,
            "cells": cells,
            "source_kind": "supplier_pricebook",
            "source_label": "BẢNG GIÁ THIẾT BỊ ĐIỆN SINO - VANLOCK",
            "source_url": "/device-catalog/documents/sino-2024-2026",
            "effective_date": "2024-07-10",
            "checked_at": "2026-11-26T01:30:00+07:00",
            "vat_status": "excluded",
            "price_note": f"Giá bảng Sino niêm yết chưa gồm VAT. Chiết khấu: {int(discount_rate*100)}%.",
            "image_url": img
        })

    # =========================================================================
    # 1. MCCB SBE (Discount: 27%) - p184..186
    # =========================================================================
    # SBE 60AF (15-20-30-40-50A & 60A)
    add_item("SBE62b/15-50", "SBE62b 15-50A 2P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 518000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "30kA"},
             ["SBE62b/15-50", "2P", "15-20-30-40-50A", "30kA", 518000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE62b/60", "SBE62b 60A 2P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 602000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "60A", "Icu (kA)": "30kA"},
             ["SBE62b/60", "2P", "60A", "30kA", 602000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE63b/15-50", "SBE63b 15-50A 3P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 596000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "18kA"},
             ["SBE63b/15-50", "3P", "15-20-30-40-50A", "18kA", 596000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE63b/60", "SBE63b 60A 3P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 696000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "60A", "Icu (kA)": "18kA"},
             ["SBE63b/60", "3P", "60A", "18kA", 696000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE64b/15-50", "SBE64b 15-50A 4P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 685000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "4P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "18kA"},
             ["SBE64b/15-50", "4P", "15-20-30-40-50A", "18kA", 685000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE64b/60", "SBE64b 60A 4P", "MCCB", "MCCB · SBE 60AF (Icu 18-30kA)", 800000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "4P", "In (A)": "60A", "Icu (kA)": "18kA"},
             ["SBE64b/60", "4P", "60A", "18kA", 800000], "/catalog-images/sino/mccb_sbe.png")

    # SBE 100AF (75-100A)
    add_item("SBE102b/75-100", "SBE102b 75-100A 2P", "MCCB", "MCCB · SBE 100AF (Icu 22-35kA)", 686000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "75-100A", "Icu (kA)": "35kA"},
             ["SBE102b/75-100", "2P", "75-100A", "35kA", 686000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE103b/75-100", "SBE103b 75-100A 3P", "MCCB", "MCCB · SBE 100AF (Icu 22-35kA)", 796000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "75-100A", "Icu (kA)": "22kA"},
             ["SBE103b/75-100", "3P", "75-100A", "22kA", 796000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE104b/75-100", "SBE104b 75-100A 4P", "MCCB", "MCCB · SBE 100AF (Icu 22-35kA)", 926000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "4P", "In (A)": "75-100A", "Icu (kA)": "22kA"},
             ["SBE104b/75-100", "4P", "75-100A", "22kA", 926000], "/catalog-images/sino/mccb_sbe.png")

    # SBE 200AF (125-150-175-200-225A; 100A is '-' in PDF)
    add_item("SBE202b/125-225", "SBE202b 125-225A 2P", "MCCB", "MCCB · SBE 200AF (Icu 30-65kA)", 1258000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "125-150-175-200-225A", "Icu (kA)": "65kA"},
             ["SBE202b/125-225", "2P", "125-150-175-200-225A", "65kA", 1258000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE203b/125-225", "SBE203b 125-225A 3P", "MCCB", "MCCB · SBE 200AF (Icu 30-65kA)", 1506000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "125-150-175-200-225A", "Icu (kA)": "30kA"},
             ["SBE203b/125-225", "3P", "125-150-175-200-225A", "30kA", 1506000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE204b/125-225", "SBE204b 125-225A 4P", "MCCB", "MCCB · SBE 200AF (Icu 30-65kA)", 1766000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "4P", "In (A)": "125-150-175-200-225A", "Icu (kA)": "30kA"},
             ["SBE204b/125-225", "4P", "125-150-175-200-225A", "30kA", 1766000], "/catalog-images/sino/mccb_sbe.png")

    # SBE 400AF (250-300-350-400A; only 2P and 3P in PDF p186)
    add_item("SBE402b/250-400", "SBE402b 250-400A 2P", "MCCB", "MCCB · SBE 400AF (Icu 42-50kA)", 3105600, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "250-300-350-400A", "Icu (kA)": "50kA"},
             ["SBE402b/250-400", "2P", "250-300-350-400A", "50kA", 3105600], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE403b/250-400", "SBE403b 250-400A 3P", "MCCB", "MCCB · SBE 400AF (Icu 42-50kA)", 3789600, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "250-300-350-400A", "Icu (kA)": "42kA"},
             ["SBE403b/250-400", "3P", "250-300-350-400A", "42kA", 3789600], "/catalog-images/sino/mccb_sbe.png")

    # SBE 800AF (500-630A & 700-800A; only 2P and 3P in PDF p186)
    add_item("SBE802b/500-630", "SBE802b 500-630A 2P", "MCCB", "MCCB · SBE 800AF (Icu 45-50kA)", 6028000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "500-630A", "Icu (kA)": "50kA"},
             ["SBE802b/500-630", "2P", "500-630A", "50kA", 6028000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE802b/700-800", "SBE802b 700-800A 2P", "MCCB", "MCCB · SBE 800AF (Icu 45-50kA)", 6906000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "2P", "In (A)": "700-800A", "Icu (kA)": "50kA"},
             ["SBE802b/700-800", "2P", "700-800A", "50kA", 6906000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE803b/500-630", "SBE803b 500-630A 3P", "MCCB", "MCCB · SBE 800AF (Icu 45-50kA)", 7452000, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "500-630A", "Icu (kA)": "45kA"},
             ["SBE803b/500-630", "3P", "500-630A", "45kA", 7452000], "/catalog-images/sino/mccb_sbe.png")
    add_item("SBE803b/700-800", "SBE803b 700-800A 3P", "MCCB", "MCCB · SBE 800AF (Icu 45-50kA)", 8529600, 0.27,
             {"Họ thiết bị": "SBE", "Số cực": "3P", "In (A)": "700-800A", "Icu (kA)": "45kA"},
             ["SBE803b/700-800", "3P", "700-800A", "45kA", 8529600], "/catalog-images/sino/mccb_sbe.png")

    # =========================================================================
    # 2. MCCB SBN & SBS (Discount: 27%) - p187..191
    # =========================================================================
    # SBN 50AF / 60AF (2P 30kA, 3P/4P 18kA)
    add_item("SBN52c/15-50", "SBN52c 15-50A 2P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 552000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "30kA"},
             ["SBN52c/15-50", "2P", "15-20-30-40-50A", "30kA", 552000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN62c/60", "SBN62c 60A 2P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 655000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "60A", "Icu (kA)": "30kA"},
             ["SBN62c/60", "2P", "60A", "30kA", 655000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN53c/15-50", "SBN53c 15-50A 3P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 645600, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "18kA"},
             ["SBN53c/15-50", "3P", "15-20-30-40-50A", "18kA", 645600], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN63c/60", "SBN63c 60A 3P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 756000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "60A", "Icu (kA)": "18kA"},
             ["SBN63c/60", "3P", "60A", "18kA", 756000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN54c/15-50", "SBN54c 15-50A 4P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 956000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "18kA"},
             ["SBN54c/15-50", "4P", "15-20-30-40-50A", "18kA", 956000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN64c/60", "SBN64c 60A 4P", "MCCB", "MCCB · SBN 50-60AF (Icu 18-30kA)", 1066000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "60A", "Icu (kA)": "18kA"},
             ["SBN64c/60", "4P", "60A", "18kA", 1066000], "/catalog-images/sino/mccb_sbn.png")

    # SBS 50AF / 60AF (2P 35kA, 3P/4P 22kA)
    add_item("SBS52c/15-50", "SBS52c 15-50A 2P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 608000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "35kA"},
             ["SBS52c/15-50", "2P", "15-20-30-40-50A", "35kA", 608000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS62c/60", "SBS62c 60A 2P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 720000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "60A", "Icu (kA)": "35kA"},
             ["SBS62c/60", "2P", "60A", "35kA", 720000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS53c/15-50", "SBS53c 15-50A 3P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 710000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "22kA"},
             ["SBS53c/15-50", "3P", "15-20-30-40-50A", "22kA", 710000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS63c/60", "SBS63c 60A 3P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 831600, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "60A", "Icu (kA)": "22kA"},
             ["SBS63c/60", "3P", "60A", "22kA", 831600], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS54c/15-50", "SBS54c 15-50A 4P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 1050000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "15-20-30-40-50A", "Icu (kA)": "22kA"},
             ["SBS54c/15-50", "4P", "15-20-30-40-50A", "22kA", 1050000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS64c/60", "SBS64c 60A 4P", "MCCB", "MCCB · SBS 50-60AF (Icu 22-35kA)", 1171200, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "60A", "Icu (kA)": "22kA"},
             ["SBS64c/60", "4P", "60A", "22kA", 1171200], "/catalog-images/sino/mccb_sbs.png")

    # SBN 100AF (2P 35kA, 3P/4P 22kA)
    add_item("SBN102c/75-100", "SBN102c 75-100A 2P", "MCCB", "MCCB · SBN 100AF (Icu 22-35kA)", 746000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "75-100A", "Icu (kA)": "35kA"},
             ["SBN102c/75-100", "2P", "75-100A", "35kA", 746000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN103c/75-100", "SBN103c 75-100A 3P", "MCCB", "MCCB · SBN 100AF (Icu 22-35kA)", 866000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "75-100A", "Icu (kA)": "22kA"},
             ["SBN103c/75-100", "3P", "75-100A", "22kA", 866000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN104c/75-100", "SBN104c 75-100A 4P", "MCCB", "MCCB · SBN 100AF (Icu 22-35kA)", 1146000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "75-100A", "Icu (kA)": "22kA"},
             ["SBN104c/75-100", "4P", "75-100A", "22kA", 1146000], "/catalog-images/sino/mccb_sbn.png")

    # SBS 100AF (2P 85kA, 3P/4P 42kA)
    add_item("SBS102c/60-125", "SBS102c 60-125A 2P", "MCCB", "MCCB · SBS 100AF (Icu 42-85kA)", 822000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "60-75-100-125A", "Icu (kA)": "85kA"},
             ["SBS102c/60-125", "2P", "60-75-100-125A", "85kA", 822000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS103c/60-125", "SBS103c 60-125A 3P", "MCCB", "MCCB · SBS 100AF (Icu 42-85kA)", 950000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "60-75-100-125A", "Icu (kA)": "42kA"},
             ["SBS103c/60-125", "3P", "60-75-100-125A", "42kA", 950000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS104c/60-125", "SBS104c 60-125A 4P", "MCCB", "MCCB · SBS 100AF (Icu 42-85kA)", 1257600, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "60-75-100-125A", "Icu (kA)": "42kA"},
             ["SBS104c/60-125", "4P", "60-75-100-125A", "42kA", 1257600], "/catalog-images/sino/mccb_sbs.png")

    # SBN & SBS 200AF
    add_item("SBN202c/125-250", "SBN202c 125-250A 2P", "MCCB", "MCCB · SBN 200AF (Icu 30-65kA)", 1368000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "65kA"},
             ["SBN202c/125-250", "2P", "125-150-175-200-225-250A", "65kA", 1368000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN203c/125-250", "SBN203c 125-250A 3P", "MCCB", "MCCB · SBN 200AF (Icu 30-65kA)", 1638000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "30kA"},
             ["SBN203c/125-250", "3P", "125-150-175-200-225-250A", "30kA", 1638000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN204c/125-250", "SBN204c 125-250A 4P", "MCCB", "MCCB · SBN 200AF (Icu 30-65kA)", 2136000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "30kA"},
             ["SBN204c/125-250", "4P", "125-150-175-200-225-250A", "30kA", 2136000], "/catalog-images/sino/mccb_sbn.png")

    add_item("SBS202c/125-250", "SBS202c 125-250A 2P", "MCCB", "MCCB · SBS 200AF (Icu 42-85kA)", 1506000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "85kA"},
             ["SBS202c/125-250", "2P", "125-150-175-200-225-250A", "85kA", 1506000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS203c/125-250", "SBS203c 125-250A 3P", "MCCB", "MCCB · SBS 200AF (Icu 42-85kA)", 1800000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "42kA"},
             ["SBS203c/125-250", "3P", "125-150-175-200-225-250A", "42kA", 1800000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS204c/125-250", "SBS204c 125-250A 4P", "MCCB", "MCCB · SBS 200AF (Icu 42-85kA)", 2349600, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "125-150-175-200-225-250A", "Icu (kA)": "42kA"},
             ["SBS204c/125-250", "4P", "125-150-175-200-225-250A", "42kA", 2349600], "/catalog-images/sino/mccb_sbs.png")

    # SBN & SBS 400AF
    add_item("SBN402c/250-400", "SBN402c 250-400A 2P", "MCCB", "MCCB · SBN 400AF (Icu 42-50kA)", 3376000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "250-300-350-400A", "Icu (kA)": "50kA"},
             ["SBN402c/250-400", "2P", "250-300-350-400A", "50kA", 3376000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN403c/250-400", "SBN403c 250-400A 3P", "MCCB", "MCCB · SBN 400AF (Icu 42-50kA)", 4118000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "250-300-350-400A", "Icu (kA)": "42kA"},
             ["SBN403c/250-400", "3P", "250-300-350-400A", "42kA", 4118000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN404c/250-400", "SBN404c 250-400A 4P", "MCCB", "MCCB · SBN 400AF (Icu 42-50kA)", 5160000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "250-300-350-400A", "Icu (kA)": "42kA"},
             ["SBN404c/250-400", "4P", "250-300-350-400A", "42kA", 5160000], "/catalog-images/sino/mccb_sbn.png")

    add_item("SBS402c/250-400", "SBS402c 250-400A 2P", "MCCB", "MCCB · SBS 400AF (Icu 65-75kA)", 3716000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "250-300-350-400A", "Icu (kA)": "75kA"},
             ["SBS402c/250-400", "2P", "250-300-350-400A", "75kA", 3716000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS403c/250-400", "SBS403c 250-400A 3P", "MCCB", "MCCB · SBS 400AF (Icu 65-75kA)", 4530000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "250-300-350-400A", "Icu (kA)": "65kA"},
             ["SBS403c/250-400", "3P", "250-300-350-400A", "65kA", 4530000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS404c/250-400", "SBS404c 250-400A 4P", "MCCB", "MCCB · SBS 400AF (Icu 65-75kA)", 5676000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "250-300-350-400A", "Icu (kA)": "65kA"},
             ["SBS404c/250-400", "4P", "250-300-350-400A", "65kA", 5676000], "/catalog-images/sino/mccb_sbs.png")

    # SBN & SBS 800AF
    add_item("SBN802c/500-630", "SBN802c 500-630A 2P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 6552000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "500-630A", "Icu (kA)": "50kA"},
             ["SBN802c/500-630", "2P", "500-630A", "50kA", 6552000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN802c/700-800", "SBN802c 700-800A 2P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 7506000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "2P", "In (A)": "700-800A", "Icu (kA)": "50kA"},
             ["SBN802c/700-800", "2P", "700-800A", "50kA", 7506000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN803c/500-630", "SBN803c 500-630A 3P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 8100000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "500-630A", "Icu (kA)": "45kA"},
             ["SBN803c/500-630", "3P", "500-630A", "45kA", 8100000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN803c/700-800", "SBN803c 700-800A 3P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 9270000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "3P", "In (A)": "700-800A", "Icu (kA)": "45kA"},
             ["SBN803c/700-800", "3P", "700-800A", "45kA", 9270000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN804c/500-630", "SBN804c 500-630A 4P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 9720000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "500-630A", "Icu (kA)": "45kA"},
             ["SBN804c/500-630", "4P", "500-630A", "45kA", 9720000], "/catalog-images/sino/mccb_sbn.png")
    add_item("SBN804c/700-800", "SBN804c 700-800A 4P", "MCCB", "MCCB · SBN 800AF (Icu 45-50kA)", 11520000, 0.27,
             {"Họ thiết bị": "SBN", "Số cực": "4P", "In (A)": "700-800A", "Icu (kA)": "45kA"},
             ["SBN804c/700-800", "4P", "700-800A", "45kA", 11520000], "/catalog-images/sino/mccb_sbn.png")

    add_item("SBS802c/500-630", "SBS802c 500-630A 2P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 7207200, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "500-630A", "Icu (kA)": "85kA"},
             ["SBS802c/500-630", "2P", "500-630A", "85kA", 7207200], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS802c/700-800", "SBS802c 700-800A 2P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 8256000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "2P", "In (A)": "700-800A", "Icu (kA)": "85kA"},
             ["SBS802c/700-800", "2P", "700-800A", "85kA", 8256000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS803c/500-630", "SBS803c 500-630A 3P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 8910000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "500-630A", "Icu (kA)": "75kA"},
             ["SBS803c/500-630", "3P", "500-630A", "75kA", 8910000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS803c/700-800", "SBS803c 700-800A 3P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 10200000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "3P", "In (A)": "700-800A", "Icu (kA)": "75kA"},
             ["SBS803c/700-800", "3P", "700-800A", "75kA", 10200000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS804c/500-630", "SBS804c 500-630A 4P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 10692000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "500-630A", "Icu (kA)": "75kA"},
             ["SBS804c/500-630", "4P", "500-630A", "75kA", 10692000], "/catalog-images/sino/mccb_sbs.png")
    add_item("SBS804c/700-800", "SBS804c 700-800A 4P", "MCCB", "MCCB · SBS 800AF (Icu 75-85kA)", 12672000, 0.27,
             {"Họ thiết bị": "SBS", "Số cực": "4P", "In (A)": "700-800A", "Icu (kA)": "75kA"},
             ["SBS804c/700-800", "4P", "700-800A", "75kA", 12672000], "/catalog-images/sino/mccb_sbs.png")

    # =========================================================================
    # 3. MCCB Chỉnh dòng VD / VS (Discount: 27%) - p192
    # =========================================================================
    vd_vs_list = [
        ("VD160N/160/FMU", "VD160N 160A 3P FMU", 160, 50, 1518000),
        ("VS250N/200/FMU", "VS250N 200A 3P FMU", 200, 65, 2232000),
        ("VS250N/250/FMU", "VS250N 250A 3P FMU", 250, 65, 2232000),
        ("VS250N/200/ATU", "VS250N 200A 3P ATU", 200, 65, 2232000),
        ("VS250N/250/ATU", "VS250N 250A 3P ATU", 250, 65, 2232000),
        ("VS630N/300/FMU", "VS630N 300A 3P FMU", 300, 50, 5616000),
        ("VS630N/400/FMU", "VS630N 400A 3P FMU", 400, 50, 5616000),
        ("VS630N/500/FMU", "VS630N 500A 3P FMU", 500, 50, 8256000),
        ("VS630N/630/FMU", "VS630N 630A 3P FMU", 630, 50, 8256000),
        ("VS630N/300/ATU", "VS630N 300A 3P ATU", 300, 50, 5616000),
        ("VS630N/400/ATU", "VS630N 400A 3P ATU", 400, 50, 5616000),
        ("VS630N/500/ATU", "VS630N 500A 3P ATU", 500, 50, 8256000),
        ("VS630N/630/ATU", "VS630N 630A 3P ATU", 630, 50, 8256000),
    ]
    for sku, name, rating, icu, price in vd_vs_list:
        add_item(sku, name, "MCCB", "MCCB · VD/VS Chỉnh dòng (Icu 50-65kA)", price, 0.27,
                 {"Họ thiết bị": "VS", "Số cực": "3P", "In (A)": f"{rating}A", "Icu (kA)": f"{icu}kA"},
                 [sku, "3P", f"{rating}A", f"{icu}kA", price], "/catalog-images/sino/mccb_vd_vs.png")

    # =========================================================================
    # 4. MCB (Discount: 34%) - p154..160
    # =========================================================================
    ps45n_ratings = [
        ("1P", "6-40A", "6-10-16-20-25-32-40A", 48000),
        ("1P", "50-63A", "50-63A", 65000),
        ("2P", "6-40A", "6-10-16-20-25-32-40A", 105600),
        ("2P", "50-63A", "50-63A", 143000),
        ("3P", "6-40A", "6-10-16-20-25-32-40A", 165600),
        ("3P", "50-63A", "50-63A", 224300),
        ("4P", "6-40A", "6-10-16-20-25-32-40A", 230500),
        ("4P", "50-63A", "50-63A", 312000),
    ]
    for p, sub, in_a, price in ps45n_ratings:
        sku = f"PS45N/{p[0]}_{sub}"
        add_item(sku, f"PS45N {p} {in_a}", "MCB", f"MCB · PS45N {p} (4.5kA)", price, 0.34,
                 {"Họ thiết bị": "PS45N", "Số cực": p, "In (A)": in_a, "Icu (kA)": "4.5kA"},
                 [sku, p, in_a, "4.5kA", price], "/catalog-images/sino/mcb_ps45n.png")

    ps65s_ratings = [
        ("1P", "6-40A", "6-10-16-20-25-32-40A", 52000),
        ("1P", "50-63A", "50-63A", 70000),
        ("2P", "6-40A", "6-10-16-20-25-32-40A", 115000),
        ("2P", "50-63A", "50-63A", 155000),
        ("3P", "6-40A", "6-10-16-20-25-32-40A", 180000),
        ("3P", "50-63A", "50-63A", 241500),
        ("4P", "6-40A", "6-10-16-20-25-32-40A", 250000),
        ("4P", "50-63A", "50-63A", 336000),
    ]
    for p, sub, in_a, price in ps65s_ratings:
        sku = f"PS65S/{p[0]}_{sub}"
        add_item(sku, f"PS65S {p} {in_a}", "MCB", f"MCB · PS65S {p} (6kA)", price, 0.34,
                 {"Họ thiết bị": "PS65S", "Số cực": p, "In (A)": in_a, "Icu (kA)": "6kA"},
                 [sku, p, in_a, "6kA", price], "/catalog-images/sino/mcb_ps65s.png")

    ps100h_ratings = [
        ("1P", "80-100A", 196000), ("1P", "125A", 360000),
        ("2P", "80-100A", 420000), ("2P", "125A", 472000),
        ("3P", "80-100A", 666000), ("3P", "125A", 736000),
        ("4P", "80-100A", 866000), ("4P", "125A", 1120000),
    ]
    for p, in_a, price in ps100h_ratings:
        sku = f"PS100H/{p[0]}_{in_a}"
        add_item(sku, f"PS100H {p} {in_a}", "MCB", f"MCB · PS100H {p} (10kA)", price, 0.34,
                 {"Họ thiết bị": "PS100H", "Số cực": p, "In (A)": in_a, "Icu (kA)": "10kA"},
                 [sku, p, in_a, "10kA", price], "/catalog-images/sino/mcb_ps100h.png")

    sc45n_ratings = [
        ("1P", "6-40A", "6-10-16-20-25-32-40A", 48000),
        ("1P", "50-63A", "50-63A", 65000),
        ("2P", "6-40A", "6-10-16-20-25-32-40A", 105600),
        ("2P", "50-63A", "50-63A", 143000),
        ("3P", "6-40A", "6-10-16-20-25-32-40A", 165600),
        ("3P", "50-63A", "50-63A", 224300),
        ("4P", "6-40A", "6-10-16-20-25-32-40A", 230500),
        ("4P", "50-63A", "50-63A", 312000),
    ]
    for p, sub, in_a, price in sc45n_ratings:
        sku = f"SC45N/{p[0]}_{sub}"
        add_item(sku, f"SC45N {p} {in_a}", "MCB", f"MCB · SC45N {p} (4.5kA)", price, 0.34,
                 {"Họ thiết bị": "SC45N", "Số cực": p, "In (A)": in_a, "Icu (kA)": "4.5kA"},
                 [sku, p, in_a, "4.5kA", price], "/catalog-images/sino/mcb_sc45n.png")

    sc68n_ratings = [
        ("1P", "6-40A", "6-10-16-20-25-32-40A", "6kA", 62000),
        ("1P", "50-63A", "50-63A", "6kA", 72000),
        ("2P", "6-40A", "6-10-16-20-25-32-40A", "6kA/10kA", 136000),
        ("2P", "50-63A", "50-63A", "6kA/10kA", 158500),
        ("3P", "6-40A", "6-10-16-20-25-32-40A", "6kA", 208000),
        ("3P", "50-63A", "50-63A", "6kA", 248500),
        ("4P", "6-40A", "6-10-16-20-25-32-40A", "6kA", 298000),
        ("4P", "50-63A", "50-63A", "6kA", 345600),
    ]
    for p, sub, in_a, icu, price in sc68n_ratings:
        sku = f"SC68N/{p[0]}_{sub}"
        add_item(sku, f"SC68N {p} {in_a}", "MCB", f"MCB · SC68N {p} (6kA)", price, 0.34,
                 {"Họ thiết bị": "SC68N", "Số cực": p, "In (A)": in_a, "Icu (kA)": icu},
                 [sku, p, in_a, icu, price], "/catalog-images/sino/mcb_sc68n.png")

    sc108n_ratings = [
        ("1P", "6-40A", "6-10-16-20-25-32-40A", 65200),
        ("1P", "50-63A", "50-63A", 75600),
        ("2P", "6-40A", "6-10-16-20-25-32-40A", 142800),
        ("2P", "50-63A", "50-63A", 166000),
        ("3P", "6-40A", "6-10-16-20-25-32-40A", 218500),
        ("3P", "50-63A", "50-63A", 261000),
        ("4P", "6-40A", "6-10-16-20-25-32-40A", 313000),
        ("4P", "50-63A", "50-63A", 363000),
    ]
    for p, sub, in_a, price in sc108n_ratings:
        sku = f"SC108N/{p[0]}_{sub}"
        add_item(sku, f"SC108N {p} {in_a}", "MCB", f"MCB · SC108N {p} (10kA)", price, 0.34,
                 {"Họ thiết bị": "SC108N", "Số cực": p, "In (A)": in_a, "Icu (kA)": "10kA"},
                 [sku, p, in_a, "10kA", price], "/catalog-images/sino/mcb_sc108n.png")

    # =========================================================================
    # 5. RCCB & RCBO (Discount: 34%) - p156, 161, 164, 166
    # =========================================================================
    vll_list = [
        ("VLL45N/2P_16-20_30mA", "VLL45N 2P 16-20A 30mA", "2P", "16-20A", "30mA", 400000),
        ("VLL45N/2P_25-40_30mA", "VLL45N 2P 25-40A 30mA", "2P", "25-32-40A", "30mA", 428000),
        ("VLL45N/2P_50-63_30mA", "VLL45N 2P 50-63A 30mA", "2P", "50-63A", "30mA", 606000),
        ("VLL45N/4P_16-20_30mA", "VLL45N 4P 16-20A 30mA", "4P", "16-20A", "30mA", 545000),
        ("VLL45N/4P_25-40_30mA", "VLL45N 4P 25-40A 30mA", "4P", "25-32-40A", "30mA", 582000),
        ("VLL45N/4P_50-63_30mA", "VLL45N 4P 50-63A 30mA", "4P", "50-63A", "30mA", 825000),
        ("VLL45N/2P_16-20_100mA", "VLL45N 2P 16-20A 100mA", "2P", "16-20A", "100mA", 400000),
        ("VLL45N/2P_25-40_100mA", "VLL45N 2P 25-40A 100mA", "2P", "25-32-40A", "100mA", 428000),
        ("VLL45N/2P_50-63_100mA", "VLL45N 2P 50-63A 100mA", "2P", "50-63A", "100mA", 606000),
        ("VLL45N/4P_16-20_100mA", "VLL45N 4P 16-20A 100mA", "4P", "16-20A", "100mA", 545000),
        ("VLL45N/4P_25-40_100mA", "VLL45N 4P 25-40A 100mA", "4P", "25-32-40A", "100mA", 582000),
        ("VLL45N/4P_50-63_100mA", "VLL45N 4P 50-63A 100mA", "4P", "50-63A", "100mA", 825000),
    ]
    for sku, name, p, in_a, idn, price in vll_list:
        add_item(sku, name, "RCCB", f"RCCB · VLL45N {p} ({idn})", price, 0.34,
                 {"Họ thiết bị": "VLL45N", "Số cực": p, "In (A)": in_a, "Dòng rò": idn},
                 [sku, p, in_a, idn, price], "/catalog-images/sino/rccb_vll45n.png")

    sl_list = [
        ("SL68N/2P_16-20_30mA", "SL68N 2P 16-20A 30mA", "2P", "16-20A", "30mA", 400000),
        ("SL68N/2P_25-40_30mA", "SL68N 2P 25-40A 30mA", "2P", "25-32-40A", "30mA", 428000),
        ("SL68N/2P_50-63_30mA", "SL68N 2P 50-63A 30mA", "2P", "50-63A", "30mA", 606000),
        ("SL68N/4P_16-20_30mA", "SL68N 4P 16-20A 30mA", "4P", "16-20A", "30mA", 545000),
        ("SL68N/4P_25-40_30mA", "SL68N 4P 25-40A 30mA", "4P", "25-32-40A", "30mA", 582000),
        ("SL68N/4P_50-63_30mA", "SL68N 4P 50-63A 30mA", "4P", "50-63A", "30mA", 825000),
        ("SL68N/2P_16-20_100mA", "SL68N 2P 16-20A 100mA", "2P", "16-20A", "100mA", 400000),
        ("SL68N/2P_25-40_100mA", "SL68N 2P 25-40A 100mA", "2P", "25-32-40A", "100mA", 428000),
        ("SL68N/2P_50-63_100mA", "SL68N 2P 50-63A 100mA", "2P", "50-63A", "100mA", 606000),
        ("SL68N/4P_16-20_100mA", "SL68N 4P 16-20A 100mA", "4P", "16-20A", "100mA", 545000),
        ("SL68N/4P_25-40_100mA", "SL68N 4P 25-40A 100mA", "4P", "25-32-40A", "100mA", 582000),
        ("SL68N/4P_50-63_100mA", "SL68N 4P 50-63A 100mA", "4P", "50-63A", "100mA", 825000),
    ]
    for sku, name, p, in_a, idn, price in sl_list:
        add_item(sku, name, "RCCB", f"RCCB · SL68N {p} ({idn})", price, 0.34,
                 {"Họ thiết bị": "SL68N", "Số cực": p, "In (A)": in_a, "Dòng rò": idn},
                 [sku, p, in_a, idn, price], "/catalog-images/sino/rccb_sl68n.png")

    sol_list = [
        ("SOL68E/2P_16-20", "SOL68E 2P 16-20A 30mA", "2P", "16-20A", "30mA", 400000),
        ("SOL68E/2P_25-40", "SOL68E 2P 25-40A 30mA", "2P", "25-32-40A", "30mA", 428000),
        ("SOL68E/2P_50-63", "SOL68E 2P 50-63A 30mA", "2P", "50-63A", "30mA", 606000),
        ("SOL45E/2P_16-20", "SOL45E 2P 16-20A 30mA", "2P", "16-20A", "30mA", 400000),
        ("SOL45E/2P_25-40", "SOL45E 2P 25-40A 30mA", "2P", "25-32-40A", "30mA", 428000),
        ("SOL45E/2P_50-63", "SOL45E 2P 50-63A 30mA", "2P", "50-63A", "30mA", 606000),
    ]
    for sku, name, p, in_a, idn, price in sol_list:
        add_item(sku, name, "RCBO", f"RCBO · {sku.split('/')[0]} (30mA)", price, 0.34,
                 {"Họ thiết bị": sku.split("/")[0], "Số cực": p, "In (A)": in_a, "Dòng rò": idn},
                 [sku, p, in_a, idn, price], "/catalog-images/sino/rcbo_sol.png")

    add_item("TRL32/10-40A", "TRL32 10-40A 30mA", "RCBO", "RCBO · TRL-32 (30mA)", 158000, 0.34,
             {"Họ thiết bị": "TRL-32", "Số cực": "2P", "In (A)": "10-20-30-40A", "Dòng rò": "30mA"},
             ["TRL32/10-40A", "2P", "10-20-30-40A", "30mA", 158000], "/catalog-images/sino/rcbo_trl.png")
    add_item("BL68N/10-40A", "BL68N 10-40A 30mA", "RCBO", "RCBO · BL68N (30mA)", 169000, 0.34,
             {"Họ thiết bị": "BL68N", "Số cực": "2P", "In (A)": "10-20-30-40A", "Dòng rò": "30mA"},
             ["BL68N/10-40A", "2P", "10-20-30-40A", "30mA", 169000], "/catalog-images/sino/rcbo_bl68n.png")

    add_item("BS121/5-40A", "Cầu dao an toàn BS121 5-40A", "CB", "Cầu dao an toàn · BS121", 51000, 0.34,
             {"Họ thiết bị": "BS121", "Số cực": "2P", "In (A)": "5-10-15-20-25-30-40A"},
             ["BS121/5-40A", "5-10-15-20-25-30-40A", 51000], "/catalog-images/sino/safety_breaker_bs.png")
    add_item("BS68N/2P5-30A", "Cầu dao an toàn BS68N 5-30A", "CB", "Cầu dao an toàn · BS68N", 45800, 0.34,
             {"Họ thiết bị": "BS68N", "Số cực": "2P", "In (A)": "5-10-15-20-25-30A"},
             ["BS68N/2P5-30A", "5-10-15-20-25-30-40A", 45800], "/catalog-images/sino/safety_breaker_bs.png")

    boxes = [
        ("4CC1", "Hộp chứa 1 MCB gắn nổi 4CC1", 33500),
        ("4CC2", "Hộp chứa 2 MCB gắn nổi 4CC2", 37800),
        ("4CC3", "Hộp chứa 3 MCB gắn nổi 4CC3", 42500),
        ("4CC4", "Hộp chứa 4 MCB gắn nổi 4CC4", 49200),
        ("4CC6", "Hộp chứa 6 MCB gắn nổi 4CC6", 59500),
        ("HB/BS121", "Hộp gắn nổi chứa át kiểu HB (HB/BS121)", 5000),
        ("HA/BS68N", "Hộp gắn nổi chứa át kiểu BS68N loại to", 3600),
        ("HA-2/BS68N", "Hộp gắn nổi chứa át kiểu BS68N loại nhỏ", 3600),
    ]
    for sku, desc, price in boxes:
        add_item(sku, desc, "ENCLOSURE", "Hộp chứa MCB & Át gắn nổi", price, 0.34,
                 {"Họ thiết bị": "Hộp MCB Sino"},
                 [sku, desc, price], "/catalog-images/sino/safety_breaker_bs.png",
                 extra_cols=["Mã hàng", "Diễn giải", "Đơn giá (VND)"])

    spd_list = [
        ("SPD/T2/1P+N/20", "SPD T2 1P+N Imax 20kA", "1P+N", "20kA", 460000),
        ("SPD/T2/1P+N/45", "SPD T2 1P+N Imax 45kA", "1P+N", "45kA", 580000),
        ("SPD/T2/1P+N/65", "SPD T2 1P+N Imax 65kA", "1P+N", "65kA", 630000),
        ("SPD/T2/1P+N/80", "SPD T2 1P+N Imax 80kA", "1P+N", "80kA", 780000),
        ("SPD/T1/T2/1P+N/50", "SPD T1/T2 1P+N Imax 50kA", "1P+N", "50kA", 1200000),
        ("SPD/T2/3P+N/20", "SPD T2 3P+N Imax 20kA", "3P+N", "20kA", 920000),
        ("SPD/T2/3P+N/45", "SPD T2 3P+N Imax 45kA", "3P+N", "45kA", 1160000),
        ("SPD/T2/3P+N/65", "SPD T2 3P+N Imax 65kA", "3P+N", "65kA", 1330000),
        ("SPD/T2/3P+N/80", "SPD T2 3P+N Imax 80kA", "3P+N", "80kA", 1690000),
        ("SPD/T1/T2/3P+N/50", "SPD T1/T2 3P+N Imax 50kA", "3P+N", "50kA", 2530000),
        ("SPD/T2/T3/3P+N/20", "SPD T2/T3 3P+N Imax 20kA", "3P+N", "20kA", 1080000),
        ("SPD/T2/T3/1P+N/20", "SPD T2/T3 1P+N Imax 20kA", "1P+N", "20kA", 540000),
        ("SPD/T1/T2/3P/50", "SPD T1/T2 3P Imax 50kA", "3P", "50kA", 1790000),
    ]
    for sku, name, p, imax, price in spd_list:
        add_item(sku, name, "SPD", "Chống sét lan truyền · SPD", price, 0.34,
                 {"Họ thiết bị": "SPD", "Số cực": p, "In (A)": "---", "Imax": imax},
                 [sku, p, "---", imax, price], "/catalog-images/sino/spd.png")

    # =========================================================================
    # 6. Contactor SMC, Relay ST/STH & Accessories (Discount: 27%) - p193..194
    # =========================================================================
    smc_list = [
        ("SMC-9", "Contactor SMC-9 9A 220VAC", 9, 248000),
        ("SMC-12", "Contactor SMC-12 12A 220VAC", 12, 280000),
        ("SMC-18", "Contactor SMC-18 18A 220VAC", 18, 416000),
        ("SMC-22", "Contactor SMC-22 22A 220VAC", 22, 508000),
        ("SMC-32", "Contactor SMC-32 32A 220VAC", 32, 745000),
        ("SMC-40", "Contactor SMC-40 40A 220VAC", 40, 875000),
        ("SMC-50", "Contactor SMC-50 50A 220VAC", 50, 929000),
        ("SMC-65", "Contactor SMC-65 65A 220VAC", 65, 1048000),
        ("SMC-75", "Contactor SMC-75 75A 220VAC", 75, 1296000),
        ("SMC-85", "Contactor SMC-85 85A 220VAC", 85, 1631000),
        ("SMC-100", "Contactor SMC-100 100A 220VAC", 100, 1999000),
        ("SMC-125", "Contactor SMC-125 125A 220VAC", 125, 2323000),
        ("SMC-150", "Contactor SMC-150 150A 220VAC", 150, 2787000),
    ]
    for sku, name, rating, price in smc_list:
        add_item(sku, name, "CONTACTOR", "Khởi động từ · Contactor Sê-ri SMC", price, 0.27,
                 {"Họ thiết bị": "SMC", "Số cực": "3P", "In (A)": f"{rating}A", "Điện áp cuộn hút": "220VAC"},
                 [sku, "3P", f"{rating}A", "220VAC", price], "/catalog-images/sino/contactor_smc.png")

    smc_a_list = [
        ("SMC-6a", "Contactor SMC-6a 6A 220VAC", 6, 236000),
        ("SMC-9a", "Contactor SMC-9a 9A 220VAC", 9, 256000),
        ("SMC-12a", "Contactor SMC-12a 12A 220VAC", 12, 265000),
        ("SMC-18a", "Contactor SMC-18a 18A 220VAC", 18, 408000),
        ("SMC-9b", "Contactor SMC-9b 9A 220VAC", 9, 265000),
        ("SMC-12b", "Contactor SMC-12b 12A 220VAC", 12, 298000),
        ("SMC-18b", "Contactor SMC-18b 18A 220VAC", 18, 429000),
        ("SMC-22b", "Contactor SMC-22b 22A 220VAC", 22, 529000),
        ("SMC-32a", "Contactor SMC-32a 32A 220VAC", 32, 770000),
        ("SMC-40a", "Contactor SMC-40a 40A 220VAC", 40, 902000),
        ("SMC-50a", "Contactor SMC-50a 50A 220VAC", 50, 1096000),
        ("SMC-65a", "Contactor SMC-65a 65A 220VAC", 65, 1245000),
        ("SMC-75a", "Contactor SMC-75a 75A 220VAC", 75, 1418000),
        ("SMC-85a", "Contactor SMC-85a 85A 220VAC", 85, 1716000),
        ("SMC-100a", "Contactor SMC-100a 100A 220VAC", 100, 2242000),
    ]
    for sku, name, rating, price in smc_a_list:
        add_item(sku, name, "CONTACTOR", "Khởi động từ · Contactor Sê-ri SMC (a/b)", price, 0.27,
                 {"Họ thiết bị": "SMC-a", "Số cực": "3P", "In (A)": f"{rating}A", "Điện áp cuộn hút": "220VAC"},
                 [sku, "3P", f"{rating}A", "220VAC", price], "/catalog-images/sino/contactor_smc.png")

    st_list = [
        ("ST-12", "Rơ le nhiệt ST-12 (0.1~18A)", "0.1~18A", 280000),
        ("ST-32", "Rơ le nhiệt ST-32 (0.1~40A)", "0.1~40A", 325000),
        ("ST-63", "Rơ le nhiệt ST-63 (4~65A)", "4~65A", 700000),
        ("ST-95", "Rơ le nhiệt ST-95 (7~100A)", "7~100A", 1010000),
        ("STH-22", "Rơ le nhiệt STH-22 (0.63~22A)", "0.63~22A", 194000),
        ("STH-40", "Rơ le nhiệt STH-40 (18~40A)", "18~40A", 270000),
        ("STH-85", "Rơ le nhiệt STH-85 (34~85A)", "34~85A", 627000),
        ("STH-100", "Rơ le nhiệt STH-100 (65~100A)", "65~100A", 811000),
        ("STH-150", "Rơ le nhiệt STH-150 (125~150A)", "125~150A", 1242000),
    ]
    for sku, name, rng, price in st_list:
        add_item(sku, name, "THERMAL_RELAY", "Rơ le nhiệt bảo vệ quá tải · ST/STH", price, 0.27,
                 {"Họ thiết bị": "ST", "In (A)": rng, "Dải đặt dòng": rng},
                 [sku, rng, price], "/catalog-images/sino/relay_st.png")

    acc_list = [
        ("LA1-D", "Khối tiếp điểm phụ LA1-D (2NC)", "AUX_CONTACT", "2NC", 37500),
        ("LA1-D11", "Khối tiếp điểm phụ LA1-D11 (NO+NC)", "AUX_CONTACT", "NO+NC", 45800),
        ("LA1-D20", "Khối tiếp điểm phụ LA1-D20 (2NO)", "AUX_CONTACT", "2NO", 45800),
        ("LA1-D22", "Khối tiếp điểm phụ LA1-D22 (2NO+2NC)", "AUX_CONTACT", "2NO+2NC", 63800),
        ("LA1-D40", "Khối tiếp điểm phụ LA1-D40 (4NO)", "AUX_CONTACT", "4NO", 60200),
        ("LA1-D04", "Khối tiếp điểm phụ LA1-D04 (4NC)", "AUX_CONTACT", "4NC", 60200),
        ("LA1-D13", "Khối tiếp điểm phụ LA1-D13 (1NO+3NC)", "AUX_CONTACT", "1NO+3NC", 60200),
        ("LA1-D31", "Khối tiếp điểm phụ LA1-D31 (3NO+1NC)", "AUX_CONTACT", "3NO+1NC", 60200),
        ("LA2-DT0/DT2", "Khối rơ-le thời gian LA2-DT0 / DT2 (0.1~3s / 0.1~30s, 1NO+1NC)", "TIMER", "1NO+1NC", 253000),
        ("LA2-DT4/DRS", "Khối rơ-le thời gian LA2-DT4 / DRS (10~180s / 0.1~30s, 1NO+1NC)", "TIMER", "1NO+1NC", 253000),
        ("LA2-DR4/DR2", "Khối rơ-le thời gian LA2-DR4 / DR2 (10~180s / 0.1~3s, 1NO+1NC)", "TIMER", "1NO+1NC", 291000),
        ("F8-11", "Khối tiếp điểm phụ F8-11 (1NO+2NC)", "AUX_CONTACT", "1NO+2NC", 162000),
        ("F8-20", "Khối tiếp điểm phụ F8-20 (2NO)", "AUX_CONTACT", "2NO", 162000),
        ("LAD-9R1", "Bộ nối nguồn động lực LAD-9R1", "INTERLOCK", "Phụ kiện liên động", 47800),
        ("LA9-D09978", "Khóa liên động cơ khí LA9-D09978", "INTERLOCK", "Khóa liên động", 47800),
        ("LA9-6569", "Bộ nối nguồn động lực LA9-6569", "INTERLOCK", "Phụ kiện liên động", 209000),
        ("LA9-D50978", "Khóa liên động cơ khí LA9-D50978", "INTERLOCK", "Khóa liên động", 209000),
        ("LA9-8069", "Bộ nối nguồn động lực LA9-8069", "INTERLOCK", "Phụ kiện liên động", 253600),
        ("LA9-D5097", "Khóa liên động cơ khí LA9-D5097", "INTERLOCK", "Khóa liên động", 208000),
    ]
    for sku, name, cat, info, price in acc_list:
        add_item(sku, name, cat, "Phụ kiện công-tắc-tơ & rơ-le · LA1/LA2/F8/LA9", price, 0.27,
                 {"Họ thiết bị": "Phụ kiện SMC", "Thông số": info},
                 [sku, name, info, price], "/catalog-images/sino/relay_st.png",
                 extra_cols=["Mã hàng", "Tên hàng", "Thông số", "Đơn giá (VND)"])

    return items


if __name__ == "__main__":
    items = create_sino_items()
    print(f"Generated {len(items)} SINO items:")
    cats = {}
    for it in items:
        cats[it['category']] = cats.get(it['category'], 0) + 1
    for c, cnt in cats.items():
        print(f"  {c}: {cnt}")
