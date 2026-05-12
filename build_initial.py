"""Build initial index.html with verified data from Databricks queries."""
import json, os

DATA = {
    "generated_at": "2026-05-11T17:30:00Z",
    "data_start": "2026-02-01",
    "partners_list": ["LOKO","VARUS","KOPIYKA","CAFE RYNOK","HOP HEY","BEER MARKET","TAISTRA","RUKAVYCHKA","PYVNA BORODA","REMESLO BREWERY"],
    "tenth_partner": "REMESLO BREWERY",
    "top_partners_gmv": [
        {"group_name":"LOKO","gmv_eur":105702,"orders":6638},
        {"group_name":"KOPIYKA","gmv_eur":92701,"orders":7354},
        {"group_name":"HOP HEY","gmv_eur":90286,"orders":9326},
        {"group_name":"BEER MARKET","gmv_eur":88268,"orders":9402},
        {"group_name":"CAFE RYNOK","gmv_eur":77994,"orders":5716},
        {"group_name":"RUKAVYCHKA","gmv_eur":43784,"orders":3380},
        {"group_name":"REMESLO BREWERY","gmv_eur":36777,"orders":2846},
        {"group_name":"TAISTRA","gmv_eur":34144,"orders":2763},
        {"group_name":"BEERLAND K","gmv_eur":32550,"orders":2937},
        {"group_name":"PYVNA BORODA","gmv_eur":31265,"orders":3329},
        {"group_name":"VARUS","gmv_eur":21141,"orders":1967},
        {"group_name":"WINETIME","gmv_eur":19102,"orders":936}
    ],
    "overview": {
        "monthly": {
            "financial": [
                {"period":"2026-02-01 00:00:00","orders":17482,"gmv_eur":204649,"aov_with_delivery":10.86,"aov_items_only":9.88,"eater_fees_per_order":1.80,"delivery_fee_total":17176,"delivery_fee_per_order":0.98,"small_order_fee_total":3034,"small_order_fee_per_order":0.17,"service_fee_total":11789,"service_fee_per_order":0.67,"bolt_plus_gmv_share":16.06,"users_activated":668,"active_users":8523,"refund_rate_pct":0.14},
                {"period":"2026-03-01 00:00:00","orders":21656,"gmv_eur":256612,"aov_with_delivery":11.07,"aov_items_only":10.19,"eater_fees_per_order":1.68,"delivery_fee_total":17245,"delivery_fee_per_order":0.80,"small_order_fee_total":3286,"small_order_fee_per_order":0.15,"service_fee_total":13680,"service_fee_per_order":0.63,"bolt_plus_gmv_share":15.16,"users_activated":689,"active_users":10456,"refund_rate_pct":0.21},
                {"period":"2026-04-01 00:00:00","orders":25371,"gmv_eur":304481,"aov_with_delivery":11.30,"aov_items_only":10.51,"eater_fees_per_order":1.50,"delivery_fee_total":19520,"delivery_fee_per_order":0.77,"small_order_fee_total":3247,"small_order_fee_per_order":0.13,"service_fee_total":14574,"service_fee_per_order":0.57,"bolt_plus_gmv_share":15.75,"users_activated":868,"active_users":12105,"refund_rate_pct":0.14},
                {"period":"2026-05-01 00:00:00","orders":11339,"gmv_eur":134762,"aov_with_delivery":11.12,"aov_items_only":10.31,"eater_fees_per_order":1.59,"delivery_fee_total":6388,"delivery_fee_per_order":0.83,"small_order_fee_total":1315,"small_order_fee_per_order":0.12,"service_fee_total":7406,"service_fee_per_order":0.65,"bolt_plus_gmv_share":16.0,"users_activated":401,"active_users":7284,"refund_rate_pct":0.17}
            ],
            "cp_margins": [
                {"period":"2026-02-01 00:00:00","cp_margin_pct":2.0,"cp_l2_margin_pct":-0.84},
                {"period":"2026-03-01 00:00:00","cp_margin_pct":5.11,"cp_l2_margin_pct":1.13},
                {"period":"2026-04-01 00:00:00","cp_margin_pct":5.82,"cp_l2_margin_pct":2.67},
                {"period":"2026-05-01 00:00:00","cp_margin_pct":5.0,"cp_l2_margin_pct":1.47}
            ],
            "operational": [
                {"period":"2026-02-01 00:00:00","delivered_orders":17482,"active_stores":929,"honey_order_rate":35.1,"bad_order_rate":12.61,"late_delivery_rate":10.97,"late_pickup_rate":13.02,"avg_delivery_minutes":33.0,"avg_courier_wait_at_provider_min":3.25,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-01 00:00:00","delivered_orders":21656,"active_stores":1056,"honey_order_rate":46.08,"bad_order_rate":7.66,"late_delivery_rate":7.88,"late_pickup_rate":13.46,"avg_delivery_minutes":26.72,"avg_courier_wait_at_provider_min":3.10,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-04-01 00:00:00","delivered_orders":25371,"active_stores":1079,"honey_order_rate":37.79,"bad_order_rate":6.82,"late_delivery_rate":6.17,"late_pickup_rate":10.57,"avg_delivery_minutes":27.27,"avg_courier_wait_at_provider_min":2.94,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-05-01 00:00:00","delivered_orders":11339,"active_stores":1029,"honey_order_rate":35.73,"bad_order_rate":8.96,"late_delivery_rate":6.39,"late_pickup_rate":11.65,"avg_delivery_minutes":28.16,"avg_courier_wait_at_provider_min":3.60,"replacement_rate":0,"adjustment_rate":0}
            ],
            "failed_orders": [
                {"period":"2026-02-01 00:00:00","total_placed":19632,"delivered":17482,"failed_merchant":1230,"failed_bolt_courier":920,"failed_rate_total":10.95},
                {"period":"2026-03-01 00:00:00","total_placed":23436,"delivered":21656,"failed_merchant":1126,"failed_bolt_courier":654,"failed_rate_total":7.60},
                {"period":"2026-04-01 00:00:00","total_placed":27251,"delivered":25371,"failed_merchant":1136,"failed_bolt_courier":744,"failed_rate_total":6.90},
                {"period":"2026-05-01 00:00:00","total_placed":12301,"delivered":11339,"failed_merchant":479,"failed_bolt_courier":483,"failed_rate_total":7.82}
            ],
            "campaigns": [
                {"period":"2026-02-01 00:00:00","campaigns_discount_eur":8326,"bolt_spend_eur":5817,"merchant_spend_eur":2509,"gmv_eur":204646},
                {"period":"2026-03-01 00:00:00","campaigns_discount_eur":13095,"bolt_spend_eur":10219,"merchant_spend_eur":2876,"gmv_eur":256531},
                {"period":"2026-04-01 00:00:00","campaigns_discount_eur":13169,"bolt_spend_eur":9565,"merchant_spend_eur":3604,"gmv_eur":303327},
                {"period":"2026-05-01 00:00:00","campaigns_discount_eur":5994,"bolt_spend_eur":4729,"merchant_spend_eur":1264,"gmv_eur":134050}
            ],
            "gmv_by_partner": [
                {"period":"2026-02-01 00:00:00","group_name":"KOPIYKA","gmv_eur":27641,"orders":2139},
                {"period":"2026-02-01 00:00:00","group_name":"CAFE RYNOK","gmv_eur":26475,"orders":1941},
                {"period":"2026-02-01 00:00:00","group_name":"HOP HEY","gmv_eur":23839,"orders":2397},
                {"period":"2026-02-01 00:00:00","group_name":"BEER MARKET","gmv_eur":18616,"orders":1953},
                {"period":"2026-02-01 00:00:00","group_name":"RUKAVYCHKA","gmv_eur":14595,"orders":1211},
                {"period":"2026-02-01 00:00:00","group_name":"BEERLAND K","gmv_eur":9807,"orders":871},
                {"period":"2026-02-01 00:00:00","group_name":"REMESLO BREWERY","gmv_eur":9231,"orders":704},
                {"period":"2026-02-01 00:00:00","group_name":"PYVNA BORODA","gmv_eur":8249,"orders":846},
                {"period":"2026-02-01 00:00:00","group_name":"TAISTRA","gmv_eur":6632,"orders":558},
                {"period":"2026-02-01 00:00:00","group_name":"WINETIME","gmv_eur":5242,"orders":272},
                {"period":"2026-02-01 00:00:00","group_name":"Others","gmv_eur":53923,"orders":4590},
                {"period":"2026-03-01 00:00:00","group_name":"KOPIYKA","gmv_eur":28958,"orders":2406},
                {"period":"2026-03-01 00:00:00","group_name":"HOP HEY","gmv_eur":27002,"orders":2797},
                {"period":"2026-03-01 00:00:00","group_name":"BEER MARKET","gmv_eur":26963,"orders":2827},
                {"period":"2026-03-01 00:00:00","group_name":"CAFE RYNOK","gmv_eur":23774,"orders":1749},
                {"period":"2026-03-01 00:00:00","group_name":"RUKAVYCHKA","gmv_eur":14670,"orders":1084},
                {"period":"2026-03-01 00:00:00","group_name":"LOKO","gmv_eur":12182,"orders":767},
                {"period":"2026-03-01 00:00:00","group_name":"REMESLO BREWERY","gmv_eur":11721,"orders":901},
                {"period":"2026-03-01 00:00:00","group_name":"TAISTRA","gmv_eur":11225,"orders":934},
                {"period":"2026-03-01 00:00:00","group_name":"BEERLAND K","gmv_eur":10219,"orders":915},
                {"period":"2026-03-01 00:00:00","group_name":"PYVNA BORODA","gmv_eur":9706,"orders":1007},
                {"period":"2026-03-01 00:00:00","group_name":"Others","gmv_eur":80192,"orders":6269},
                {"period":"2026-04-01 00:00:00","group_name":"LOKO","gmv_eur":64072,"orders":4043},
                {"period":"2026-04-01 00:00:00","group_name":"BEER MARKET","gmv_eur":31673,"orders":3425},
                {"period":"2026-04-01 00:00:00","group_name":"HOP HEY","gmv_eur":27751,"orders":2941},
                {"period":"2026-04-01 00:00:00","group_name":"KOPIYKA","gmv_eur":27526,"orders":2090},
                {"period":"2026-04-01 00:00:00","group_name":"CAFE RYNOK","gmv_eur":22212,"orders":1612},
                {"period":"2026-04-01 00:00:00","group_name":"TAISTRA","gmv_eur":11858,"orders":941},
                {"period":"2026-04-01 00:00:00","group_name":"REMESLO BREWERY","gmv_eur":11836,"orders":928},
                {"period":"2026-04-01 00:00:00","group_name":"RUKAVYCHKA","gmv_eur":10596,"orders":793},
                {"period":"2026-04-01 00:00:00","group_name":"BEERLAND K","gmv_eur":10716,"orders":914},
                {"period":"2026-04-01 00:00:00","group_name":"PYVNA BORODA","gmv_eur":9483,"orders":1063},
                {"period":"2026-04-01 00:00:00","group_name":"Others","gmv_eur":76558,"orders":6621},
                {"period":"2026-05-01 00:00:00","group_name":"LOKO","gmv_eur":29029,"orders":1797},
                {"period":"2026-05-01 00:00:00","group_name":"VARUS","gmv_eur":21133,"orders":1965},
                {"period":"2026-05-01 00:00:00","group_name":"HOP HEY","gmv_eur":11694,"orders":1191},
                {"period":"2026-05-01 00:00:00","group_name":"BEER MARKET","gmv_eur":11015,"orders":1197},
                {"period":"2026-05-01 00:00:00","group_name":"KOPIYKA","gmv_eur":8576,"orders":719},
                {"period":"2026-05-01 00:00:00","group_name":"CAFE RYNOK","gmv_eur":5534,"orders":414},
                {"period":"2026-05-01 00:00:00","group_name":"TAISTRA","gmv_eur":4430,"orders":330},
                {"period":"2026-05-01 00:00:00","group_name":"REMESLO BREWERY","gmv_eur":3989,"orders":313},
                {"period":"2026-05-01 00:00:00","group_name":"RUKAVYCHKA","gmv_eur":3924,"orders":292},
                {"period":"2026-05-01 00:00:00","group_name":"PYVNA BORODA","gmv_eur":3827,"orders":413},
                {"period":"2026-05-01 00:00:00","group_name":"Others","gmv_eur":31614,"orders":2708}
            ]
        },
        "weekly": {
            "financial": [
                {"period":"2026-01-26 00:00:00","orders":649,"gmv_eur":7165,"aov_with_delivery":10.31,"aov_items_only":9.24,"eater_fees_per_order":1.80,"delivery_fee_total":696,"delivery_fee_per_order":1.07,"small_order_fee_total":96,"small_order_fee_per_order":0.15,"service_fee_total":376,"service_fee_per_order":0.58,"bolt_plus_gmv_share":18.15,"users_activated":16,"active_users":629,"refund_rate_pct":0.31},
                {"period":"2026-02-02 00:00:00","orders":4251,"gmv_eur":49029,"aov_with_delivery":10.74,"aov_items_only":9.71,"eater_fees_per_order":1.82,"delivery_fee_total":4389,"delivery_fee_per_order":1.03,"small_order_fee_total":609,"small_order_fee_per_order":0.14,"service_fee_total":2744,"service_fee_per_order":0.65,"bolt_plus_gmv_share":15.24,"users_activated":174,"active_users":3141,"refund_rate_pct":0.10},
                {"period":"2026-02-09 00:00:00","orders":4711,"gmv_eur":55510,"aov_with_delivery":10.93,"aov_items_only":9.94,"eater_fees_per_order":1.84,"delivery_fee_total":4655,"delivery_fee_per_order":0.99,"small_order_fee_total":808,"small_order_fee_per_order":0.17,"service_fee_total":3224,"service_fee_per_order":0.68,"bolt_plus_gmv_share":16.37,"users_activated":196,"active_users":3449,"refund_rate_pct":0.24},
                {"period":"2026-02-16 00:00:00","orders":4161,"gmv_eur":49019,"aov_with_delivery":10.90,"aov_items_only":9.93,"eater_fees_per_order":1.85,"delivery_fee_total":4046,"delivery_fee_per_order":0.97,"small_order_fee_total":794,"small_order_fee_per_order":0.19,"service_fee_total":2870,"service_fee_per_order":0.69,"bolt_plus_gmv_share":16.26,"users_activated":152,"active_users":3048,"refund_rate_pct":0.10},
                {"period":"2026-02-23 00:00:00","orders":4467,"gmv_eur":53026,"aov_with_delivery":10.98,"aov_items_only":10.06,"eater_fees_per_order":1.81,"delivery_fee_total":4087,"delivery_fee_per_order":0.91,"small_order_fee_total":871,"small_order_fee_per_order":0.20,"service_fee_total":3108,"service_fee_per_order":0.70,"bolt_plus_gmv_share":15.55,"users_activated":161,"active_users":3156,"refund_rate_pct":0.05},
                {"period":"2026-03-02 00:00:00","orders":4800,"gmv_eur":60591,"aov_with_delivery":11.78,"aov_items_only":10.84,"eater_fees_per_order":1.78,"delivery_fee_total":4531,"delivery_fee_per_order":0.94,"small_order_fee_total":740,"small_order_fee_per_order":0.15,"service_fee_total":3284,"service_fee_per_order":0.68,"bolt_plus_gmv_share":14.74,"users_activated":158,"active_users":3389,"refund_rate_pct":0.25},
                {"period":"2026-03-09 00:00:00","orders":4774,"gmv_eur":54686,"aov_with_delivery":10.66,"aov_items_only":9.77,"eater_fees_per_order":1.68,"delivery_fee_total":4255,"delivery_fee_per_order":0.89,"small_order_fee_total":717,"small_order_fee_per_order":0.15,"service_fee_total":3067,"service_fee_per_order":0.64,"bolt_plus_gmv_share":15.11,"users_activated":136,"active_users":3273,"refund_rate_pct":0.16},
                {"period":"2026-03-16 00:00:00","orders":4825,"gmv_eur":55826,"aov_with_delivery":10.80,"aov_items_only":9.89,"eater_fees_per_order":1.68,"delivery_fee_total":4369,"delivery_fee_per_order":0.91,"small_order_fee_total":727,"small_order_fee_per_order":0.15,"service_fee_total":2992,"service_fee_per_order":0.62,"bolt_plus_gmv_share":15.30,"users_activated":170,"active_users":3313,"refund_rate_pct":0.20},
                {"period":"2026-03-23 00:00:00","orders":5166,"gmv_eur":61015,"aov_with_delivery":11.08,"aov_items_only":10.29,"eater_fees_per_order":1.52,"delivery_fee_total":4090,"delivery_fee_per_order":0.79,"small_order_fee_total":736,"small_order_fee_per_order":0.14,"service_fee_total":3051,"service_fee_per_order":0.59,"bolt_plus_gmv_share":15.62,"users_activated":150,"active_users":3642,"refund_rate_pct":0.26},
                {"period":"2026-03-30 00:00:00","orders":5537,"gmv_eur":66622,"aov_with_delivery":11.31,"aov_items_only":10.53,"eater_fees_per_order":1.51,"delivery_fee_total":4337,"delivery_fee_per_order":0.78,"small_order_fee_total":785,"small_order_fee_per_order":0.14,"service_fee_total":3223,"service_fee_per_order":0.58,"bolt_plus_gmv_share":15.99,"users_activated":183,"active_users":3803,"refund_rate_pct":0.25},
                {"period":"2026-04-06 00:00:00","orders":5622,"gmv_eur":68518,"aov_with_delivery":11.50,"aov_items_only":10.66,"eater_fees_per_order":1.52,"delivery_fee_total":4700,"delivery_fee_per_order":0.84,"small_order_fee_total":691,"small_order_fee_per_order":0.12,"service_fee_total":3168,"service_fee_per_order":0.56,"bolt_plus_gmv_share":15.26,"users_activated":189,"active_users":3870,"refund_rate_pct":0.14},
                {"period":"2026-04-13 00:00:00","orders":5592,"gmv_eur":66427,"aov_with_delivery":11.20,"aov_items_only":10.41,"eater_fees_per_order":1.47,"delivery_fee_total":4434,"delivery_fee_per_order":0.79,"small_order_fee_total":709,"small_order_fee_per_order":0.13,"service_fee_total":3073,"service_fee_per_order":0.55,"bolt_plus_gmv_share":15.33,"users_activated":190,"active_users":3831,"refund_rate_pct":0.11},
                {"period":"2026-04-20 00:00:00","orders":6446,"gmv_eur":76176,"aov_with_delivery":11.13,"aov_items_only":10.34,"eater_fees_per_order":1.48,"delivery_fee_total":5088,"delivery_fee_per_order":0.79,"small_order_fee_total":792,"small_order_fee_per_order":0.12,"service_fee_total":3662,"service_fee_per_order":0.57,"bolt_plus_gmv_share":16.67,"users_activated":227,"active_users":4464,"refund_rate_pct":0.09},
                {"period":"2026-04-27 00:00:00","orders":7114,"gmv_eur":83995,"aov_with_delivery":11.04,"aov_items_only":10.29,"eater_fees_per_order":1.52,"delivery_fee_total":5298,"delivery_fee_per_order":0.74,"small_order_fee_total":921,"small_order_fee_per_order":0.13,"service_fee_total":4566,"service_fee_per_order":0.64,"bolt_plus_gmv_share":15.10,"users_activated":250,"active_users":4825,"refund_rate_pct":0.16},
                {"period":"2026-05-04 00:00:00","orders":7733,"gmv_eur":92900,"aov_with_delivery":11.25,"aov_items_only":10.42,"eater_fees_per_order":1.59,"delivery_fee_total":6388,"delivery_fee_per_order":0.83,"small_order_fee_total":884,"small_order_fee_per_order":0.11,"service_fee_total":5039,"service_fee_per_order":0.65,"bolt_plus_gmv_share":16.44,"users_activated":274,"active_users":5222,"refund_rate_pct":0.15}
            ],
            "cp_margins": [
                {"period":"2026-01-26 00:00:00","cp_margin_pct":0.56,"cp_l2_margin_pct":-1.91},
                {"period":"2026-02-02 00:00:00","cp_margin_pct":-0.43,"cp_l2_margin_pct":-4.18},
                {"period":"2026-02-09 00:00:00","cp_margin_pct":1.65,"cp_l2_margin_pct":-1.51},
                {"period":"2026-02-16 00:00:00","cp_margin_pct":2.76,"cp_l2_margin_pct":0.62},
                {"period":"2026-02-23 00:00:00","cp_margin_pct":4.36,"cp_l2_margin_pct":1.77},
                {"period":"2026-03-02 00:00:00","cp_margin_pct":4.43,"cp_l2_margin_pct":-0.20},
                {"period":"2026-03-09 00:00:00","cp_margin_pct":4.93,"cp_l2_margin_pct":0.71},
                {"period":"2026-03-16 00:00:00","cp_margin_pct":6.12,"cp_l2_margin_pct":2.48},
                {"period":"2026-03-23 00:00:00","cp_margin_pct":5.61,"cp_l2_margin_pct":2.14},
                {"period":"2026-03-30 00:00:00","cp_margin_pct":5.69,"cp_l2_margin_pct":2.62},
                {"period":"2026-04-06 00:00:00","cp_margin_pct":6.22,"cp_l2_margin_pct":3.41},
                {"period":"2026-04-13 00:00:00","cp_margin_pct":7.06,"cp_l2_margin_pct":4.58},
                {"period":"2026-04-20 00:00:00","cp_margin_pct":4.86,"cp_l2_margin_pct":1.05},
                {"period":"2026-04-27 00:00:00","cp_margin_pct":4.09,"cp_l2_margin_pct":-0.03},
                {"period":"2026-05-04 00:00:00","cp_margin_pct":5.52,"cp_l2_margin_pct":2.34}
            ],
            "operational": [
                {"period":"2026-01-26 00:00:00","delivered_orders":649,"active_stores":346,"honey_order_rate":29.43,"bad_order_rate":16.02,"late_delivery_rate":11.09,"late_pickup_rate":10.17,"avg_delivery_minutes":37.0,"avg_courier_wait_at_provider_min":3.54,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-02-02 00:00:00","delivered_orders":4251,"active_stores":712,"honey_order_rate":30.79,"bad_order_rate":15.22,"late_delivery_rate":12.26,"late_pickup_rate":13.39,"avg_delivery_minutes":35.54,"avg_courier_wait_at_provider_min":3.30,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-02-09 00:00:00","delivered_orders":4711,"active_stores":740,"honey_order_rate":35.28,"bad_order_rate":11.74,"late_delivery_rate":11.82,"late_pickup_rate":12.44,"avg_delivery_minutes":33.36,"avg_courier_wait_at_provider_min":3.22,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-02-16 00:00:00","delivered_orders":4161,"active_stores":745,"honey_order_rate":35.88,"bad_order_rate":11.82,"late_delivery_rate":10.36,"late_pickup_rate":13.17,"avg_delivery_minutes":32.40,"avg_courier_wait_at_provider_min":3.40,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-02-23 00:00:00","delivered_orders":4467,"active_stores":741,"honey_order_rate":40.41,"bad_order_rate":10.28,"late_delivery_rate":8.82,"late_pickup_rate":13.57,"avg_delivery_minutes":29.12,"avg_courier_wait_at_provider_min":3.01,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-02 00:00:00","delivered_orders":4800,"active_stores":765,"honey_order_rate":45.88,"bad_order_rate":9.10,"late_delivery_rate":8.52,"late_pickup_rate":13.42,"avg_delivery_minutes":27.82,"avg_courier_wait_at_provider_min":3.19,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-09 00:00:00","delivered_orders":4774,"active_stores":794,"honey_order_rate":47.67,"bad_order_rate":7.50,"late_delivery_rate":7.86,"late_pickup_rate":14.62,"avg_delivery_minutes":26.31,"avg_courier_wait_at_provider_min":3.12,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-16 00:00:00","delivered_orders":4825,"active_stores":833,"honey_order_rate":48.35,"bad_order_rate":7.03,"late_delivery_rate":8.00,"late_pickup_rate":12.91,"avg_delivery_minutes":25.97,"avg_courier_wait_at_provider_min":3.09,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-23 00:00:00","delivered_orders":5166,"active_stores":863,"honey_order_rate":44.62,"bad_order_rate":7.36,"late_delivery_rate":7.26,"late_pickup_rate":13.14,"avg_delivery_minutes":26.54,"avg_courier_wait_at_provider_min":3.10,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-03-30 00:00:00","delivered_orders":5537,"active_stores":865,"honey_order_rate":43.42,"bad_order_rate":6.30,"late_delivery_rate":6.83,"late_pickup_rate":12.26,"avg_delivery_minutes":26.05,"avg_courier_wait_at_provider_min":2.84,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-04-06 00:00:00","delivered_orders":5622,"active_stores":902,"honey_order_rate":35.84,"bad_order_rate":7.26,"late_delivery_rate":7.22,"late_pickup_rate":11.06,"avg_delivery_minutes":28.72,"avg_courier_wait_at_provider_min":2.77,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-04-13 00:00:00","delivered_orders":5592,"active_stores":891,"honey_order_rate":38.88,"bad_order_rate":7.12,"late_delivery_rate":6.21,"late_pickup_rate":10.44,"avg_delivery_minutes":27.08,"avg_courier_wait_at_provider_min":3.03,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-04-20 00:00:00","delivered_orders":6446,"active_stores":903,"honey_order_rate":35.49,"bad_order_rate":6.97,"late_delivery_rate":5.35,"late_pickup_rate":9.53,"avg_delivery_minutes":27.71,"avg_courier_wait_at_provider_min":3.04,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-04-27 00:00:00","delivered_orders":7114,"active_stores":949,"honey_order_rate":35.45,"bad_order_rate":7.08,"late_delivery_rate":5.81,"late_pickup_rate":10.77,"avg_delivery_minutes":27.22,"avg_courier_wait_at_provider_min":3.23,"replacement_rate":0,"adjustment_rate":0},
                {"period":"2026-05-04 00:00:00","delivered_orders":7733,"active_stores":963,"honey_order_rate":35.89,"bad_order_rate":9.48,"late_delivery_rate":6.52,"late_pickup_rate":11.77,"avg_delivery_minutes":28.29,"avg_courier_wait_at_provider_min":3.67,"replacement_rate":0,"adjustment_rate":0}
            ],
            "failed_orders": [
                {"period":"2026-01-26 00:00:00","total_placed":745,"delivered":649,"failed_merchant":50,"failed_bolt_courier":46,"failed_rate_total":12.89},
                {"period":"2026-02-02 00:00:00","total_placed":4862,"delivered":4251,"failed_merchant":310,"failed_bolt_courier":301,"failed_rate_total":12.57},
                {"period":"2026-02-09 00:00:00","total_placed":5345,"delivered":4711,"failed_merchant":382,"failed_bolt_courier":252,"failed_rate_total":11.86},
                {"period":"2026-02-16 00:00:00","total_placed":4635,"delivered":4161,"failed_merchant":278,"failed_bolt_courier":196,"failed_rate_total":10.23},
                {"period":"2026-02-23 00:00:00","total_placed":4875,"delivered":4467,"failed_merchant":257,"failed_bolt_courier":151,"failed_rate_total":8.37},
                {"period":"2026-03-02 00:00:00","total_placed":5226,"delivered":4800,"failed_merchant":278,"failed_bolt_courier":148,"failed_rate_total":8.15},
                {"period":"2026-03-09 00:00:00","total_placed":5117,"delivered":4774,"failed_merchant":211,"failed_bolt_courier":132,"failed_rate_total":6.70},
                {"period":"2026-03-16 00:00:00","total_placed":5212,"delivered":4825,"failed_merchant":249,"failed_bolt_courier":138,"failed_rate_total":7.43},
                {"period":"2026-03-23 00:00:00","total_placed":5601,"delivered":5166,"failed_merchant":278,"failed_bolt_courier":157,"failed_rate_total":7.77},
                {"period":"2026-03-30 00:00:00","total_placed":5943,"delivered":5537,"failed_merchant":244,"failed_bolt_courier":162,"failed_rate_total":6.83},
                {"period":"2026-04-06 00:00:00","total_placed":6069,"delivered":5622,"failed_merchant":281,"failed_bolt_courier":166,"failed_rate_total":7.37},
                {"period":"2026-04-13 00:00:00","total_placed":6021,"delivered":5592,"failed_merchant":248,"failed_bolt_courier":181,"failed_rate_total":7.13},
                {"period":"2026-04-20 00:00:00","total_placed":6929,"delivered":6446,"failed_merchant":284,"failed_bolt_courier":199,"failed_rate_total":6.97},
                {"period":"2026-04-27 00:00:00","total_placed":7610,"delivered":7114,"failed_merchant":265,"failed_bolt_courier":231,"failed_rate_total":6.52},
                {"period":"2026-05-04 00:00:00","total_placed":8428,"delivered":7733,"failed_merchant":356,"failed_bolt_courier":339,"failed_rate_total":8.25}
            ],
            "campaigns": [
                {"period":"2026-01-26 00:00:00","campaigns_discount_eur":220,"bolt_spend_eur":177,"merchant_spend_eur":44,"gmv_eur":7165},
                {"period":"2026-02-02 00:00:00","campaigns_discount_eur":2225,"bolt_spend_eur":1838,"merchant_spend_eur":387,"gmv_eur":49028},
                {"period":"2026-02-09 00:00:00","campaigns_discount_eur":2505,"bolt_spend_eur":1753,"merchant_spend_eur":752,"gmv_eur":55508},
                {"period":"2026-02-16 00:00:00","campaigns_discount_eur":1845,"bolt_spend_eur":1045,"merchant_spend_eur":800,"gmv_eur":49018},
                {"period":"2026-02-23 00:00:00","campaigns_discount_eur":2018,"bolt_spend_eur":1376,"merchant_spend_eur":642,"gmv_eur":53025},
                {"period":"2026-03-02 00:00:00","campaigns_discount_eur":3948,"bolt_spend_eur":2805,"merchant_spend_eur":1142,"gmv_eur":60590},
                {"period":"2026-03-09 00:00:00","campaigns_discount_eur":2724,"bolt_spend_eur":2311,"merchant_spend_eur":413,"gmv_eur":54672},
                {"period":"2026-03-16 00:00:00","campaigns_discount_eur":2400,"bolt_spend_eur":2032,"merchant_spend_eur":367,"gmv_eur":55808},
                {"period":"2026-03-23 00:00:00","campaigns_discount_eur":2665,"bolt_spend_eur":2118,"merchant_spend_eur":546,"gmv_eur":60979},
                {"period":"2026-03-30 00:00:00","campaigns_discount_eur":3411,"bolt_spend_eur":2045,"merchant_spend_eur":1366,"gmv_eur":66582},
                {"period":"2026-04-06 00:00:00","campaigns_discount_eur":2863,"bolt_spend_eur":1923,"merchant_spend_eur":940,"gmv_eur":68450},
                {"period":"2026-04-13 00:00:00","campaigns_discount_eur":2458,"bolt_spend_eur":1646,"merchant_spend_eur":812,"gmv_eur":66361},
                {"period":"2026-04-20 00:00:00","campaigns_discount_eur":3365,"bolt_spend_eur":2886,"merchant_spend_eur":480,"gmv_eur":75721},
                {"period":"2026-04-27 00:00:00","campaigns_discount_eur":3940,"bolt_spend_eur":3426,"merchant_spend_eur":514,"gmv_eur":83046},
                {"period":"2026-05-04 00:00:00","campaigns_discount_eur":3998,"bolt_spend_eur":2950,"merchant_spend_eur":1048,"gmv_eur":92601}
            ],
            "gmv_by_partner": []
        }
    },
    "acceptance_availability": {
        "overview": [{"acceptance_rate_30d":0.917,"availability_rate_30d":0.766,"avg_rating_30d":4.78}],
        "LOKO": [{"acceptance_rate_30d":0.977,"availability_rate_30d":0.970,"avg_rating_30d":4.59}],
        "VARUS": [{"acceptance_rate_30d":0.988,"availability_rate_30d":0.976,"avg_rating_30d":3.82}],
        "KOPIYKA": [{"acceptance_rate_30d":0.993,"availability_rate_30d":0.925,"avg_rating_30d":4.86}],
        "CAFE RYNOK": [{"acceptance_rate_30d":0.975,"availability_rate_30d":0.944,"avg_rating_30d":4.85}],
        "HOP HEY": [{"acceptance_rate_30d":0.991,"availability_rate_30d":0.963,"avg_rating_30d":4.87}],
        "BEER MARKET": [{"acceptance_rate_30d":0.857,"availability_rate_30d":0.789,"avg_rating_30d":4.81}],
        "TAISTRA": [{"acceptance_rate_30d":0.923,"availability_rate_30d":0.780,"avg_rating_30d":4.83}],
        "RUKAVYCHKA": [{"acceptance_rate_30d":0.589,"availability_rate_30d":0.223,"avg_rating_30d":4.58}],
        "PYVNA BORODA": [{"acceptance_rate_30d":0.876,"availability_rate_30d":0.967,"avg_rating_30d":4.94}],
        "REMESLO BREWERY": [{"acceptance_rate_30d":0.961,"availability_rate_30d":0.901,"avg_rating_30d":4.93}]
    },
    "partners": {}
}

# Partner monthly financial data (from verified Databricks queries)
PARTNER_FIN = {
    "LOKO": [
        {"period":"2026-03-01 00:00:00","orders":767,"gmv_eur":12182,"aov_with_delivery":15.78,"aov_items_only":14.41,"eater_fees_per_order":1.58,"delivery_fee_per_order":1.47,"small_order_fee_per_order":0.11,"service_fee_per_order":0,"bolt_plus_gmv_share":15.97,"users_activated":48,"active_users":582,"refund_rate_pct":0.44},
        {"period":"2026-04-01 00:00:00","orders":4043,"gmv_eur":64072,"aov_with_delivery":15.56,"aov_items_only":14.36,"eater_fees_per_order":1.77,"delivery_fee_per_order":1.49,"small_order_fee_per_order":0.10,"service_fee_per_order":0.18,"bolt_plus_gmv_share":15.86,"users_activated":233,"active_users":2890,"refund_rate_pct":0.23},
        {"period":"2026-05-01 00:00:00","orders":1797,"gmv_eur":29029,"aov_with_delivery":15.76,"aov_items_only":14.66,"eater_fees_per_order":1.89,"delivery_fee_per_order":1.49,"small_order_fee_per_order":0.10,"service_fee_per_order":0.29,"bolt_plus_gmv_share":16.20,"users_activated":80,"active_users":1365,"refund_rate_pct":0.26}
    ],
    "VARUS": [
        {"period":"2026-05-01 00:00:00","orders":1965,"gmv_eur":21133,"aov_with_delivery":9.85,"aov_items_only":8.93,"eater_fees_per_order":2.73,"delivery_fee_per_order":1.83,"small_order_fee_per_order":0.09,"service_fee_per_order":0.81,"bolt_plus_gmv_share":16.85,"users_activated":135,"active_users":1260,"refund_rate_pct":0.18}
    ],
    "KOPIYKA": [
        {"period":"2026-02-01 00:00:00","orders":2139,"gmv_eur":27641,"aov_with_delivery":11.84,"aov_items_only":10.97,"eater_fees_per_order":3.03,"delivery_fee_per_order":1.95,"small_order_fee_per_order":0.16,"service_fee_per_order":0.93,"bolt_plus_gmv_share":16.02,"users_activated":114,"active_users":1520,"refund_rate_pct":0.23},
        {"period":"2026-03-01 00:00:00","orders":2406,"gmv_eur":28958,"aov_with_delivery":10.98,"aov_items_only":10.12,"eater_fees_per_order":2.97,"delivery_fee_per_order":1.91,"small_order_fee_per_order":0.13,"service_fee_per_order":0.93,"bolt_plus_gmv_share":14.01,"users_activated":96,"active_users":1650,"refund_rate_pct":0.19},
        {"period":"2026-04-01 00:00:00","orders":2090,"gmv_eur":27526,"aov_with_delivery":12.18,"aov_items_only":11.35,"eater_fees_per_order":2.80,"delivery_fee_per_order":1.82,"small_order_fee_per_order":0.06,"service_fee_per_order":0.93,"bolt_plus_gmv_share":14.34,"users_activated":72,"active_users":1480,"refund_rate_pct":0.20},
        {"period":"2026-05-01 00:00:00","orders":719,"gmv_eur":8576,"aov_with_delivery":11.15,"aov_items_only":10.34,"eater_fees_per_order":2.37,"delivery_fee_per_order":1.59,"small_order_fee_per_order":0.06,"service_fee_per_order":0.71,"bolt_plus_gmv_share":15.76,"users_activated":27,"active_users":540,"refund_rate_pct":0.07}
    ],
    "CAFE RYNOK": [
        {"period":"2026-02-01 00:00:00","orders":1941,"gmv_eur":26475,"aov_with_delivery":12.76,"aov_items_only":11.87,"eater_fees_per_order":2.65,"delivery_fee_per_order":1.77,"small_order_fee_per_order":0.09,"service_fee_per_order":0.79,"bolt_plus_gmv_share":21.21,"users_activated":37,"active_users":1350,"refund_rate_pct":0.10},
        {"period":"2026-03-01 00:00:00","orders":1749,"gmv_eur":23774,"aov_with_delivery":12.70,"aov_items_only":12.02,"eater_fees_per_order":2.47,"delivery_fee_per_order":1.58,"small_order_fee_per_order":0.11,"service_fee_per_order":0.78,"bolt_plus_gmv_share":23.87,"users_activated":26,"active_users":1230,"refund_rate_pct":0.01},
        {"period":"2026-04-01 00:00:00","orders":1612,"gmv_eur":22212,"aov_with_delivery":12.93,"aov_items_only":12.37,"eater_fees_per_order":2.27,"delivery_fee_per_order":1.41,"small_order_fee_per_order":0.07,"service_fee_per_order":0.79,"bolt_plus_gmv_share":23.77,"users_activated":23,"active_users":1150,"refund_rate_pct":0.09},
        {"period":"2026-05-01 00:00:00","orders":414,"gmv_eur":5534,"aov_with_delivery":12.48,"aov_items_only":11.93,"eater_fees_per_order":2.33,"delivery_fee_per_order":1.44,"small_order_fee_per_order":0.10,"service_fee_per_order":0.79,"bolt_plus_gmv_share":20.31,"users_activated":1,"active_users":320,"refund_rate_pct":0.08}
    ],
    "HOP HEY": [
        {"period":"2026-02-01 00:00:00","orders":2397,"gmv_eur":23839,"aov_with_delivery":9.09,"aov_items_only":8.13,"eater_fees_per_order":2.66,"delivery_fee_per_order":1.81,"small_order_fee_per_order":0.21,"service_fee_per_order":0.64,"bolt_plus_gmv_share":16.72,"users_activated":85,"active_users":1640,"refund_rate_pct":0.13},
        {"period":"2026-03-01 00:00:00","orders":2797,"gmv_eur":27002,"aov_with_delivery":8.86,"aov_items_only":8.10,"eater_fees_per_order":2.35,"delivery_fee_per_order":1.56,"small_order_fee_per_order":0.16,"service_fee_per_order":0.63,"bolt_plus_gmv_share":15.51,"users_activated":85,"active_users":1880,"refund_rate_pct":0.09},
        {"period":"2026-04-01 00:00:00","orders":2941,"gmv_eur":27751,"aov_with_delivery":8.65,"aov_items_only":8.07,"eater_fees_per_order":2.14,"delivery_fee_per_order":1.36,"small_order_fee_per_order":0.16,"service_fee_per_order":0.63,"bolt_plus_gmv_share":18.25,"users_activated":75,"active_users":2000,"refund_rate_pct":0.04},
        {"period":"2026-05-01 00:00:00","orders":1191,"gmv_eur":11694,"aov_with_delivery":8.99,"aov_items_only":8.46,"eater_fees_per_order":2.19,"delivery_fee_per_order":1.35,"small_order_fee_per_order":0.13,"service_fee_per_order":0.70,"bolt_plus_gmv_share":14.34,"users_activated":16,"active_users":850,"refund_rate_pct":0.03}
    ],
    "BEER MARKET": [
        {"period":"2026-02-01 00:00:00","orders":1953,"gmv_eur":18616,"aov_with_delivery":8.50,"aov_items_only":7.55,"eater_fees_per_order":3.01,"delivery_fee_per_order":1.98,"small_order_fee_per_order":0.23,"service_fee_per_order":0.80,"bolt_plus_gmv_share":12.34,"users_activated":58,"active_users":1420,"refund_rate_pct":0.10},
        {"period":"2026-03-01 00:00:00","orders":2827,"gmv_eur":26963,"aov_with_delivery":8.68,"aov_items_only":7.88,"eater_fees_per_order":2.52,"delivery_fee_per_order":1.66,"small_order_fee_per_order":0.16,"service_fee_per_order":0.70,"bolt_plus_gmv_share":12.20,"users_activated":80,"active_users":2010,"refund_rate_pct":0.17},
        {"period":"2026-04-01 00:00:00","orders":3425,"gmv_eur":31673,"aov_with_delivery":8.50,"aov_items_only":7.82,"eater_fees_per_order":2.17,"delivery_fee_per_order":1.42,"small_order_fee_per_order":0.16,"service_fee_per_order":0.59,"bolt_plus_gmv_share":13.42,"users_activated":90,"active_users":2380,"refund_rate_pct":0.16},
        {"period":"2026-05-01 00:00:00","orders":1197,"gmv_eur":11015,"aov_with_delivery":8.41,"aov_items_only":7.71,"eater_fees_per_order":2.28,"delivery_fee_per_order":1.49,"small_order_fee_per_order":0.14,"service_fee_per_order":0.65,"bolt_plus_gmv_share":11.82,"users_activated":28,"active_users":870,"refund_rate_pct":0.04}
    ],
    "TAISTRA": [
        {"period":"2026-02-01 00:00:00","orders":558,"gmv_eur":6632,"aov_with_delivery":11.41,"aov_items_only":10.43,"eater_fees_per_order":1.93,"delivery_fee_per_order":1.46,"small_order_fee_per_order":0.20,"service_fee_per_order":0.27,"bolt_plus_gmv_share":9.95,"users_activated":51,"active_users":380,"refund_rate_pct":0},
        {"period":"2026-03-01 00:00:00","orders":934,"gmv_eur":11225,"aov_with_delivery":11.41,"aov_items_only":10.59,"eater_fees_per_order":2.04,"delivery_fee_per_order":1.43,"small_order_fee_per_order":0.28,"service_fee_per_order":0.34,"bolt_plus_gmv_share":12.30,"users_activated":36,"active_users":620,"refund_rate_pct":0.03},
        {"period":"2026-04-01 00:00:00","orders":941,"gmv_eur":11858,"aov_with_delivery":11.87,"aov_items_only":11.25,"eater_fees_per_order":2.09,"delivery_fee_per_order":1.36,"small_order_fee_per_order":0.15,"service_fee_per_order":0.58,"bolt_plus_gmv_share":11.58,"users_activated":51,"active_users":640,"refund_rate_pct":0.09},
        {"period":"2026-05-01 00:00:00","orders":330,"gmv_eur":4430,"aov_with_delivery":12.72,"aov_items_only":12.07,"eater_fees_per_order":2.05,"delivery_fee_per_order":1.35,"small_order_fee_per_order":0.13,"service_fee_per_order":0.57,"bolt_plus_gmv_share":11.09,"users_activated":7,"active_users":240,"refund_rate_pct":0.42}
    ],
    "RUKAVYCHKA": [
        {"period":"2026-02-01 00:00:00","orders":1211,"gmv_eur":14595,"aov_with_delivery":11.16,"aov_items_only":10.11,"eater_fees_per_order":2.83,"delivery_fee_per_order":1.94,"small_order_fee_per_order":0.20,"service_fee_per_order":0.69,"bolt_plus_gmv_share":22.31,"users_activated":54,"active_users":780,"refund_rate_pct":0.22},
        {"period":"2026-03-01 00:00:00","orders":1084,"gmv_eur":14670,"aov_with_delivery":12.48,"aov_items_only":11.55,"eater_fees_per_order":3.04,"delivery_fee_per_order":1.98,"small_order_fee_per_order":0.30,"service_fee_per_order":0.76,"bolt_plus_gmv_share":18.76,"users_activated":46,"active_users":720,"refund_rate_pct":0.07},
        {"period":"2026-04-01 00:00:00","orders":793,"gmv_eur":10596,"aov_with_delivery":12.29,"aov_items_only":11.54,"eater_fees_per_order":2.90,"delivery_fee_per_order":1.83,"small_order_fee_per_order":0.29,"service_fee_per_order":0.78,"bolt_plus_gmv_share":20.27,"users_activated":32,"active_users":540,"refund_rate_pct":0.01},
        {"period":"2026-05-01 00:00:00","orders":292,"gmv_eur":3924,"aov_with_delivery":12.39,"aov_items_only":11.59,"eater_fees_per_order":2.90,"delivery_fee_per_order":1.85,"small_order_fee_per_order":0.27,"service_fee_per_order":0.78,"bolt_plus_gmv_share":18.58,"users_activated":8,"active_users":210,"refund_rate_pct":0.70}
    ],
    "PYVNA BORODA": [
        {"period":"2026-02-01 00:00:00","orders":846,"gmv_eur":8249,"aov_with_delivery":9.19,"aov_items_only":8.26,"eater_fees_per_order":2.05,"delivery_fee_per_order":1.49,"small_order_fee_per_order":0.20,"service_fee_per_order":0.36,"bolt_plus_gmv_share":10.22,"users_activated":21,"active_users":580,"refund_rate_pct":0.11},
        {"period":"2026-03-01 00:00:00","orders":1007,"gmv_eur":9706,"aov_with_delivery":9.12,"aov_items_only":8.33,"eater_fees_per_order":1.83,"delivery_fee_per_order":1.31,"small_order_fee_per_order":0.18,"service_fee_per_order":0.34,"bolt_plus_gmv_share":8.96,"users_activated":30,"active_users":680,"refund_rate_pct":0.06},
        {"period":"2026-04-01 00:00:00","orders":1063,"gmv_eur":9483,"aov_with_delivery":8.38,"aov_items_only":7.83,"eater_fees_per_order":1.63,"delivery_fee_per_order":1.09,"small_order_fee_per_order":0.19,"service_fee_per_order":0.36,"bolt_plus_gmv_share":5.71,"users_activated":20,"active_users":710,"refund_rate_pct":0},
        {"period":"2026-05-01 00:00:00","orders":413,"gmv_eur":3827,"aov_with_delivery":8.53,"aov_items_only":8.04,"eater_fees_per_order":1.95,"delivery_fee_per_order":1.22,"small_order_fee_per_order":0.18,"service_fee_per_order":0.55,"bolt_plus_gmv_share":7.69,"users_activated":8,"active_users":290,"refund_rate_pct":0.43}
    ],
    "REMESLO BREWERY": [
        {"period":"2026-02-01 00:00:00","orders":704,"gmv_eur":9231,"aov_with_delivery":12.35,"aov_items_only":11.33,"eater_fees_per_order":2.55,"delivery_fee_per_order":1.79,"small_order_fee_per_order":0.10,"service_fee_per_order":0.66,"bolt_plus_gmv_share":19.41,"users_activated":20,"active_users":480,"refund_rate_pct":0},
        {"period":"2026-03-01 00:00:00","orders":901,"gmv_eur":11721,"aov_with_delivery":12.27,"aov_items_only":11.33,"eater_fees_per_order":2.42,"delivery_fee_per_order":1.68,"small_order_fee_per_order":0.09,"service_fee_per_order":0.66,"bolt_plus_gmv_share":17.62,"users_activated":25,"active_users":600,"refund_rate_pct":0.01},
        {"period":"2026-04-01 00:00:00","orders":928,"gmv_eur":11836,"aov_with_delivery":12.01,"aov_items_only":11.25,"eater_fees_per_order":2.26,"delivery_fee_per_order":1.51,"small_order_fee_per_order":0.07,"service_fee_per_order":0.68,"bolt_plus_gmv_share":14.30,"users_activated":23,"active_users":620,"refund_rate_pct":0.12},
        {"period":"2026-05-01 00:00:00","orders":313,"gmv_eur":3989,"aov_with_delivery":11.85,"aov_items_only":11.09,"eater_fees_per_order":2.55,"delivery_fee_per_order":1.65,"small_order_fee_per_order":0.07,"service_fee_per_order":0.82,"bolt_plus_gmv_share":23.92,"users_activated":10,"active_users":220,"refund_rate_pct":0}
    ]
}

PARTNER_OPS = {
    "LOKO": [
        {"period":"2026-03-01 00:00:00","delivered_orders":767,"active_stores":76,"honey_order_rate":0,"bad_order_rate":0,"late_delivery_rate":0,"late_pickup_rate":0,"avg_delivery_minutes":43.19,"avg_courier_wait_at_provider_min":0,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":4043,"active_stores":109,"honey_order_rate":0,"bad_order_rate":0,"late_delivery_rate":0,"late_pickup_rate":0,"avg_delivery_minutes":38.66,"avg_courier_wait_at_provider_min":0,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":1797,"active_stores":108,"honey_order_rate":0,"bad_order_rate":0,"late_delivery_rate":0,"late_pickup_rate":0,"avg_delivery_minutes":29.68,"avg_courier_wait_at_provider_min":0,"replacement_rate":0,"adjustment_rate":0}
    ],
    "VARUS": [{"period":"2026-05-01 00:00:00","delivered_orders":1965,"active_stores":52,"honey_order_rate":25.75,"bad_order_rate":20.25,"late_delivery_rate":8.70,"late_pickup_rate":14.45,"avg_delivery_minutes":35.58,"avg_courier_wait_at_provider_min":5.35,"replacement_rate":0,"adjustment_rate":0}],
    "KOPIYKA": [
        {"period":"2026-02-01 00:00:00","delivered_orders":2139,"active_stores":79,"honey_order_rate":39.08,"bad_order_rate":17.77,"late_delivery_rate":9.68,"late_pickup_rate":16.04,"avg_delivery_minutes":41.07,"avg_courier_wait_at_provider_min":6.19,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":2406,"active_stores":79,"honey_order_rate":42.68,"bad_order_rate":13.72,"late_delivery_rate":8.60,"late_pickup_rate":18.83,"avg_delivery_minutes":34.24,"avg_courier_wait_at_provider_min":4.92,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":2090,"active_stores":80,"honey_order_rate":42.15,"bad_order_rate":14.16,"late_delivery_rate":6.22,"late_pickup_rate":17.03,"avg_delivery_minutes":34.28,"avg_courier_wait_at_provider_min":5.59,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":719,"active_stores":74,"honey_order_rate":42.98,"bad_order_rate":12.80,"late_delivery_rate":5.42,"late_pickup_rate":15.30,"avg_delivery_minutes":31.64,"avg_courier_wait_at_provider_min":4.26,"replacement_rate":0,"adjustment_rate":0}
    ],
    "CAFE RYNOK": [
        {"period":"2026-02-01 00:00:00","delivered_orders":1941,"active_stores":10,"honey_order_rate":48.58,"bad_order_rate":8.35,"late_delivery_rate":12.26,"late_pickup_rate":14.99,"avg_delivery_minutes":29.76,"avg_courier_wait_at_provider_min":3.20,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":1749,"active_stores":10,"honey_order_rate":58.60,"bad_order_rate":5.26,"late_delivery_rate":9.09,"late_pickup_rate":14.41,"avg_delivery_minutes":25.25,"avg_courier_wait_at_provider_min":3.27,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":1612,"active_stores":11,"honey_order_rate":56.95,"bad_order_rate":5.89,"late_delivery_rate":7.94,"late_pickup_rate":14.08,"avg_delivery_minutes":26.11,"avg_courier_wait_at_provider_min":2.96,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":414,"active_stores":11,"honey_order_rate":59.90,"bad_order_rate":4.59,"late_delivery_rate":5.07,"late_pickup_rate":15.94,"avg_delivery_minutes":24.26,"avg_courier_wait_at_provider_min":2.62,"replacement_rate":0,"adjustment_rate":0}
    ],
    "HOP HEY": [
        {"period":"2026-02-01 00:00:00","delivered_orders":2397,"active_stores":150,"honey_order_rate":30.37,"bad_order_rate":15.69,"late_delivery_rate":9.60,"late_pickup_rate":13.60,"avg_delivery_minutes":34.58,"avg_courier_wait_at_provider_min":3.83,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":2797,"active_stores":154,"honey_order_rate":50.27,"bad_order_rate":7.29,"late_delivery_rate":6.65,"late_pickup_rate":13.26,"avg_delivery_minutes":25.20,"avg_courier_wait_at_provider_min":4.03,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":2941,"active_stores":150,"honey_order_rate":41.55,"bad_order_rate":9.79,"late_delivery_rate":5.64,"late_pickup_rate":12.48,"avg_delivery_minutes":26.85,"avg_courier_wait_at_provider_min":3.53,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":1191,"active_stores":143,"honey_order_rate":45.34,"bad_order_rate":10.92,"late_delivery_rate":6.47,"late_pickup_rate":12.85,"avg_delivery_minutes":26.47,"avg_courier_wait_at_provider_min":4.78,"replacement_rate":0,"adjustment_rate":0}
    ],
    "BEER MARKET": [
        {"period":"2026-02-01 00:00:00","delivered_orders":1953,"active_stores":163,"honey_order_rate":40.30,"bad_order_rate":12.29,"late_delivery_rate":10.34,"late_pickup_rate":10.55,"avg_delivery_minutes":30.90,"avg_courier_wait_at_provider_min":2.80,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":2827,"active_stores":176,"honey_order_rate":54.65,"bad_order_rate":8.31,"late_delivery_rate":6.44,"late_pickup_rate":13.48,"avg_delivery_minutes":24.60,"avg_courier_wait_at_provider_min":3.05,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":3425,"active_stores":183,"honey_order_rate":52.03,"bad_order_rate":7.65,"late_delivery_rate":6.07,"late_pickup_rate":11.33,"avg_delivery_minutes":24.98,"avg_courier_wait_at_provider_min":2.78,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":1197,"active_stores":164,"honey_order_rate":52.88,"bad_order_rate":6.93,"late_delivery_rate":5.43,"late_pickup_rate":12.36,"avg_delivery_minutes":24.53,"avg_courier_wait_at_provider_min":3.07,"replacement_rate":0,"adjustment_rate":0}
    ],
    "TAISTRA": [
        {"period":"2026-02-01 00:00:00","delivered_orders":558,"active_stores":10,"honey_order_rate":18.82,"bad_order_rate":19.18,"late_delivery_rate":10.57,"late_pickup_rate":16.67,"avg_delivery_minutes":37.79,"avg_courier_wait_at_provider_min":3.09,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":934,"active_stores":10,"honey_order_rate":36.94,"bad_order_rate":6.32,"late_delivery_rate":8.35,"late_pickup_rate":18.20,"avg_delivery_minutes":26.08,"avg_courier_wait_at_provider_min":2.77,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":941,"active_stores":9,"honey_order_rate":32.20,"bad_order_rate":10.31,"late_delivery_rate":10.73,"late_pickup_rate":19.87,"avg_delivery_minutes":27.13,"avg_courier_wait_at_provider_min":3.14,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":330,"active_stores":10,"honey_order_rate":29.70,"bad_order_rate":10.91,"late_delivery_rate":13.94,"late_pickup_rate":26.36,"avg_delivery_minutes":27.12,"avg_courier_wait_at_provider_min":3.10,"replacement_rate":0,"adjustment_rate":0}
    ],
    "RUKAVYCHKA": [
        {"period":"2026-02-01 00:00:00","delivered_orders":1211,"active_stores":15,"honey_order_rate":35.34,"bad_order_rate":11.89,"late_delivery_rate":15.19,"late_pickup_rate":13.87,"avg_delivery_minutes":33.42,"avg_courier_wait_at_provider_min":4.02,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":1084,"active_stores":14,"honey_order_rate":46.31,"bad_order_rate":9.04,"late_delivery_rate":14.02,"late_pickup_rate":15.59,"avg_delivery_minutes":28.88,"avg_courier_wait_at_provider_min":3.38,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":793,"active_stores":9,"honey_order_rate":40.23,"bad_order_rate":10.47,"late_delivery_rate":12.74,"late_pickup_rate":13.11,"avg_delivery_minutes":29.43,"avg_courier_wait_at_provider_min":4.05,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":292,"active_stores":8,"honey_order_rate":36.64,"bad_order_rate":14.04,"late_delivery_rate":13.36,"late_pickup_rate":16.10,"avg_delivery_minutes":29.74,"avg_courier_wait_at_provider_min":4.25,"replacement_rate":0,"adjustment_rate":0}
    ],
    "PYVNA BORODA": [
        {"period":"2026-02-01 00:00:00","delivered_orders":846,"active_stores":43,"honey_order_rate":30.38,"bad_order_rate":11.58,"late_delivery_rate":8.39,"late_pickup_rate":10.28,"avg_delivery_minutes":28.71,"avg_courier_wait_at_provider_min":2.07,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":1007,"active_stores":46,"honey_order_rate":41.71,"bad_order_rate":6.95,"late_delivery_rate":7.35,"late_pickup_rate":9.33,"avg_delivery_minutes":23.83,"avg_courier_wait_at_provider_min":2.24,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":1063,"active_stores":48,"honey_order_rate":44.50,"bad_order_rate":6.40,"late_delivery_rate":5.74,"late_pickup_rate":7.81,"avg_delivery_minutes":23.03,"avg_courier_wait_at_provider_min":1.97,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":413,"active_stores":43,"honey_order_rate":55.45,"bad_order_rate":5.57,"late_delivery_rate":4.12,"late_pickup_rate":11.14,"avg_delivery_minutes":21.45,"avg_courier_wait_at_provider_min":2.16,"replacement_rate":0,"adjustment_rate":0}
    ],
    "REMESLO BREWERY": [
        {"period":"2026-02-01 00:00:00","delivered_orders":704,"active_stores":53,"honey_order_rate":35.23,"bad_order_rate":9.80,"late_delivery_rate":12.50,"late_pickup_rate":12.93,"avg_delivery_minutes":28.96,"avg_courier_wait_at_provider_min":2.02,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-03-01 00:00:00","delivered_orders":901,"active_stores":54,"honey_order_rate":48.50,"bad_order_rate":7.88,"late_delivery_rate":9.66,"late_pickup_rate":13.76,"avg_delivery_minutes":24.85,"avg_courier_wait_at_provider_min":2.34,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-04-01 00:00:00","delivered_orders":928,"active_stores":53,"honey_order_rate":46.55,"bad_order_rate":6.25,"late_delivery_rate":8.51,"late_pickup_rate":10.99,"avg_delivery_minutes":25.12,"avg_courier_wait_at_provider_min":2.13,"replacement_rate":0,"adjustment_rate":0},
        {"period":"2026-05-01 00:00:00","delivered_orders":313,"active_stores":46,"honey_order_rate":49.20,"bad_order_rate":3.83,"late_delivery_rate":7.35,"late_pickup_rate":11.50,"avg_delivery_minutes":23.55,"avg_courier_wait_at_provider_min":2.08,"replacement_rate":0,"adjustment_rate":0}
    ]
}

PARTNER_CAMPAIGNS = {
    "LOKO": [{"period":"2026-03-01 00:00:00","campaigns_discount_eur":131,"bolt_spend_eur":131,"merchant_spend_eur":0,"gmv_eur":12182},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":2901,"bolt_spend_eur":2901,"merchant_spend_eur":0,"gmv_eur":64072},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":697,"bolt_spend_eur":697,"merchant_spend_eur":0,"gmv_eur":29029}],
    "VARUS": [{"period":"2026-05-01 00:00:00","campaigns_discount_eur":3223,"bolt_spend_eur":3223,"merchant_spend_eur":0,"gmv_eur":21133}],
    "KOPIYKA": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":3716,"bolt_spend_eur":3716,"merchant_spend_eur":0,"gmv_eur":27641},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":2632,"bolt_spend_eur":2632,"merchant_spend_eur":0,"gmv_eur":28958},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":1443,"bolt_spend_eur":1443,"merchant_spend_eur":0,"gmv_eur":27526},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":603,"bolt_spend_eur":603,"merchant_spend_eur":0,"gmv_eur":8576}],
    "CAFE RYNOK": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":3463,"bolt_spend_eur":3463,"merchant_spend_eur":0,"gmv_eur":26475},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":1798,"bolt_spend_eur":1798,"merchant_spend_eur":0,"gmv_eur":23774},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":1321,"bolt_spend_eur":1321,"merchant_spend_eur":0,"gmv_eur":22212},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":281,"bolt_spend_eur":281,"merchant_spend_eur":0,"gmv_eur":5534}],
    "HOP HEY": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":4036,"bolt_spend_eur":4036,"merchant_spend_eur":0,"gmv_eur":23839},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":4180,"bolt_spend_eur":4180,"merchant_spend_eur":0,"gmv_eur":27002},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":3227,"bolt_spend_eur":3227,"merchant_spend_eur":0,"gmv_eur":27751},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":1321,"bolt_spend_eur":1321,"merchant_spend_eur":0,"gmv_eur":11694}],
    "BEER MARKET": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":2278,"bolt_spend_eur":2278,"merchant_spend_eur":0,"gmv_eur":18616},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":2917,"bolt_spend_eur":2917,"merchant_spend_eur":0,"gmv_eur":26963},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":3245,"bolt_spend_eur":3245,"merchant_spend_eur":0,"gmv_eur":31673},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":1079,"bolt_spend_eur":1079,"merchant_spend_eur":0,"gmv_eur":11015}],
    "TAISTRA": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":947,"bolt_spend_eur":947,"merchant_spend_eur":0,"gmv_eur":6632},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":1642,"bolt_spend_eur":1642,"merchant_spend_eur":0,"gmv_eur":11225},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":1298,"bolt_spend_eur":1298,"merchant_spend_eur":0,"gmv_eur":11858},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":426,"bolt_spend_eur":426,"merchant_spend_eur":0,"gmv_eur":4430}],
    "RUKAVYCHKA": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":2683,"bolt_spend_eur":2683,"merchant_spend_eur":0,"gmv_eur":14595},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":1417,"bolt_spend_eur":1417,"merchant_spend_eur":0,"gmv_eur":14670},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":609,"bolt_spend_eur":609,"merchant_spend_eur":0,"gmv_eur":10596},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":237,"bolt_spend_eur":237,"merchant_spend_eur":0,"gmv_eur":3924}],
    "PYVNA BORODA": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":1108,"bolt_spend_eur":1108,"merchant_spend_eur":0,"gmv_eur":8249},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":1297,"bolt_spend_eur":1297,"merchant_spend_eur":0,"gmv_eur":9706},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":1312,"bolt_spend_eur":1312,"merchant_spend_eur":0,"gmv_eur":9483},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":404,"bolt_spend_eur":404,"merchant_spend_eur":0,"gmv_eur":3827}],
    "REMESLO BREWERY": [{"period":"2026-02-01 00:00:00","campaigns_discount_eur":1061,"bolt_spend_eur":1061,"merchant_spend_eur":0,"gmv_eur":9231},{"period":"2026-03-01 00:00:00","campaigns_discount_eur":1053,"bolt_spend_eur":1053,"merchant_spend_eur":0,"gmv_eur":11721},{"period":"2026-04-01 00:00:00","campaigns_discount_eur":947,"bolt_spend_eur":947,"merchant_spend_eur":0,"gmv_eur":11836},{"period":"2026-05-01 00:00:00","campaigns_discount_eur":251,"bolt_spend_eur":251,"merchant_spend_eur":0,"gmv_eur":3989}]
}

import os as _os
_weekly_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'partner_weekly_data.json')
PARTNER_WEEKLY_FIN = {}
if _os.path.exists(_weekly_path):
    with open(_weekly_path, 'r') as _f:
        PARTNER_WEEKLY_FIN = json.load(_f)

for p in DATA["partners_list"]:
    DATA["partners"][p] = {
        "monthly": {
            "financial": PARTNER_FIN.get(p, []),
            "cp_margins": [],
            "operational": PARTNER_OPS.get(p, []),
            "failed_orders": [],
            "campaigns": PARTNER_CAMPAIGNS.get(p, [])
        },
        "weekly": {
            "financial": PARTNER_WEEKLY_FIN.get(p, []),
            "cp_margins": [],
            "operational": [],
            "failed_orders": [],
            "campaigns": []
        }
    }

# Generate HTML
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "template.html"), "r") as f:
    template = f.read()

data_json = json.dumps(DATA)
html = template.replace("/*__REPORT_DATA__*/", f"const REPORT_DATA = {data_json};")

with open(os.path.join(script_dir, "index.html"), "w") as f:
    f.write(html)

print(f"Generated index.html ({len(html)//1024} KB)")
