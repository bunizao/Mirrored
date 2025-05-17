// 2025-05-18 00:47:57

(() => {
    const urlObj = new URL($context.url);
    const path = urlObj.pathname;

    const body = $response.body;
    if (!body) return $done({});

    let data;
    try {
        data = JSON.parse(body);
    } catch (e) {
        console.error("JSON 解析失败:", e.message);
        return $done({});
    }

    const { media, items } = data;

    if (path === '/luna/me/recently-played-media') {
        if (Array.isArray(media)) {
            data.media = media.filter(item => item.type !== 'video');
        }
    } else if (path === '/luna/feed/song-tab') {
        if (Array.isArray(items)) {
            data.items = items.filter(item => item.type !== 'video_track_mix');
        }
    } else {
        return $done({});
    }

    $done({
        body: JSON.stringify(data),
        headers: $response.headers
    });
})();
