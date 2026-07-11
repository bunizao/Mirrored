/*
https://t.me/ibilibili
2026-07-11 19:18:08
*/

let body = $response.body || "";

const KEEP_SERVER_DATA_KEYS = new Set([
  "fastBindCMobilePreCheck",
  "queryStationPackageInfo",
]);

function removeGifContainers(html) {
  const classMarker = 'class="index_gif-container';
  let searchFrom = 0;

  while (true) {
    const classIndex = html.indexOf(classMarker, searchFrom);
    if (classIndex === -1) break;

    const divStart = html.lastIndexOf("<div", classIndex);
    if (divStart === -1) {
      searchFrom = classIndex + classMarker.length;
      continue;
    }

    const openTagEnd = html.indexOf(">", divStart);
    if (openTagEnd === -1 || openTagEnd < classIndex) {
      searchFrom = classIndex + classMarker.length;
      continue;
    }

    const divEnd = findElementEnd(html, divStart);
    if (divEnd === -1) {
      searchFrom = classIndex + classMarker.length;
      continue;
    }

    html = html.slice(0, divStart) + html.slice(divEnd);
    searchFrom = divStart;
  }

  return html;
}

function findElementEnd(html, startIndex) {
  let index = startIndex;
  let depth = 0;

  while (index < html.length) {
    const nextOpen = html.indexOf("<div", index);
    const nextClose = html.indexOf("</div>", index);

    if (nextClose === -1) return -1;

    if (nextOpen !== -1 && nextOpen < nextClose) {
      depth += 1;
      index = nextOpen + 4;
      continue;
    }

    depth -= 1;
    index = nextClose + 6;

    if (depth === 0) return index;
  }

  return -1;
}

function trimNextData(html) {
  const scriptStart = html.indexOf('<script id="__NEXT_DATA__"');
  if (scriptStart === -1) return html;

  const openEnd = html.indexOf(">", scriptStart);
  if (openEnd === -1) return html;

  const scriptEnd = html.indexOf("</script>", openEnd);
  if (scriptEnd === -1) return html;

  const rawJson = html.slice(openEnd + 1, scriptEnd);

  try {
    const data = JSON.parse(rawJson);
    const serverData = data?.props?.pageProps?.serverData;

    if (Array.isArray(serverData)) {
      data.props.pageProps.serverData = serverData.filter((item) =>
        KEEP_SERVER_DATA_KEYS.has(item && item.key)
      );
    }

    return (
      html.slice(0, openEnd + 1) +
      JSON.stringify(data) +
      html.slice(scriptEnd)
    );
  } catch (e) {
    console.log("__NEXT_DATA__ parse failed: " + e.message);
    return html;
  }
}

body = removeGifContainers(body);
body = trimNextData(body);

$done({ body });