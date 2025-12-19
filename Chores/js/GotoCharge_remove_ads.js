// 2025-12-20 01:53:16

(() => {
    // 1. 初始健壮性检查
    if (!$response?.body) return $done({});
    
    let outerBody;
    try {
        // 解析最外层JSON
        outerBody = JSON.parse($response.body);
    } catch (e) {
        console.log(`[Error] 外层JSON解析失败: ${e.message}`);
        return $done({});
    }

    // 2. 获取并解析内层配置JSON字符串
    const configContentStr = outerBody?.data?.ConfigContent;
    if (typeof configContentStr !== 'string') {
        console.log("[Info] 未找到有效的 ConfigContent 字符串，跳过处理。");
        return $done({});
    }

    let innerConfig;
    try {
        innerConfig = JSON.parse(configContentStr);
    } catch (e) {
        console.log(`[Error] 内层JSON解析失败: ${e.message}`);
        return $done({});
    }

    // 3. 定义需要修改的规则 (使用 Set 以提高查找性能)
    
    /** 需将其值修改为 "0" 的键名集合 */
    const KEYS_TO_ZERO = new Set([
        "ADSDKSwitch",
        "ADSDKSwitchType",
        "isActivityActive",
        "newCommentActivity",
        "shopCard"
    ]);

    /** 需要删除的键名集合 */
    const KEYS_TO_DELETE = new Set([
        "rechargeAd", "rechargeAdOpenEW", "newPlusBanner", "alipayUnionActivity",
        "mainPageBottomIcon", "plusDesc", "chargingAD", "signin", "meFuncs580",
        "wonderfulActivitiesTitle", "loginImgURL", "loginMeImgURL",
        "batteryCareProductImg", "shopCouponURL", "orderPrizeDrawBeginTime",
        "orderPrizeDrawEndTime", "orderPrizeDrawChargeAmmount",
        "redEnvelopedRainTime", "redEnvelopedRainNotCity", "findTabContent",
        "alipayPlusDiscount", "answerHint"
    ]);

    // 4. 核心修改逻辑封装
    /**
     * 根据规则修改配置对象
     * @param {object} config - 待修改的配置对象
     * @param {Set<string>} zeroSet - 需置零的键名集合
     * @param {Set<string>} deleteSet - 需删除的键名集合
     * @returns {{ deleted: string[], zeroed: string[] }} 记录了所有变更的对象
     */
    function modifyConfig(config, zeroSet, deleteSet) {
        const changes = { deleted: [], zeroed: [] };

        for (const key in config) {
            // 使用 hasOwnProperty 确保只处理对象自身的属性
            if (Object.prototype.hasOwnProperty.call(config, key)) {
                if (deleteSet.has(key)) {
                    delete config[key];
                    changes.deleted.push(key);
                } else if (zeroSet.has(key) && config[key] !== "0") {
                    config[key] = "0";
                    changes.zeroed.push(key);
                }
            }
        }
        return changes;
    }

    // 5. 执行修改
    const changes = modifyConfig(innerConfig, KEYS_TO_ZERO, KEYS_TO_DELETE);
    const hasChanges = changes.deleted.length > 0 || changes.zeroed.length > 0;

    // 6. 重组响应体并返回
    if (hasChanges) {
        console.log("[Success] 配置已修改:", changes);
        try {
            outerBody.data.ConfigContent = JSON.stringify(innerConfig);
            return $done({ body: JSON.stringify(outerBody) });
        } catch (e) {
            console.log(`[Error] 响应体重组失败: ${e.message}`);
            return $done({});
        }
    }

    console.log("[Info] 配置未发现需要修改的项。");
    return $done({})();
})();