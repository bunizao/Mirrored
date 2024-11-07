/*
引用地址 https://raw.githubusercontent.com/RuCu6/Loon/main/Scripts/xiaohongshu.js
*/
// 2024-11-07 14:00

const url = $request.url;
if (!$response.body) $done({});
let obj = JSON.parse($response.body);

if (url.includes("/v1/note/imagefeed") || url.includes("/v2/note/feed")) {
  // 信息流 图片
  let newDatas = [];
  if (obj?.data?.[0]?.note_list?.length > 0) {
    for (let item of obj.data[0].note_list) {
      if (item?.media_save_config) {
        // 水印开关
        item.media_save_config.disable_save = false;
        item.media_save_config.disable_watermark = true;
        item.media_save_config.disable_weibo_cover = true;
      }
      if (item?.share_info?.function_entries?.length > 0) {
        // 下载限制
        const additem = { type: "video_download" };
        let func = item.share_info.function_entries[0];
        if (func?.type !== "video_download") {
          // 向数组开头添加对象
          item.share_info.function_entries.unshift(additem);
        }
      }
      if (item?.images_list?.length > 0) {
        for (let i of item.images_list) {
          if (i.hasOwnProperty("live_photo_file_id") && i.hasOwnProperty("live_photo")) {
            if (
              i?.live_photo_file_id !== "" &&
              i?.live_photo?.media?.video_id !== "" &&
              i?.live_photo?.media?.stream?.h265?.[0]?.master_url !== ""
            ) {
              let myData = {
                file_id: i.live_photo_file_id,
                video_id: i.live_photo.media.video_id,
                url: i.live_photo.media.stream.h265[0].master_url
              };
              newDatas.push(myData);
            }
            // 写入持久化存储
            $persistentStore.write(JSON.stringify(newDatas), "redBookLivePhoto");
          }
        }
      }
    }
  }
} else if (url.includes("/v1/note/live_photo/save")) {
  // 实况照片保存请求
  let livePhoto = JSON.parse($persistentStore.read("redBookLivePhoto")); // 读取持久化存储
  if (obj?.data?.datas?.length > 0) {
    // 原始数据没问题 交换url数据
    if (livePhoto?.length > 0) {
      obj.data.datas.forEach((itemA) => {
        livePhoto.forEach((itemB) => {
          if (itemB?.file_id === itemA?.file_id && itemA?.url !== "") {
            itemA.url = itemA.url.replace(/^https?:\/\/.*\.mp4$/g, itemB.url);
          }
        });
      });
    }
  } else {
    // 原始数据有问题 强制返回成功响应
    obj = { code: 0, success: true, msg: "成功", data: { datas: livePhoto } };
  }
} else if (url.includes("/v1/system_service/config")) {
  // 整体配置
  const item = ["app_theme", "loading_img", "splash", "store"];
  if (obj?.data) {
    for (let i of item) {
      delete obj.data[i];
    }
  }
} else if (url.includes("/v2/note/widgets")) {
  // 详情页小部件
  const item = ["cooperate_binds", "generic", "note_next_step"];
  // cooperate_binds合作品牌 note_next_step活动
  if (obj?.data) {
    for (let i of item) {
      delete obj.data[i];
    }
  }
} else if (url.includes("/v2/system_service/splash_config")) {
  // 开屏广告
  if (obj?.data?.ads_groups?.length > 0) {
    for (let i of obj.data.ads_groups) {
      i.start_time = 3818332800; // Unix 时间戳 2090-12-31 00:00:00
      i.end_time = 3818419199; // Unix 时间戳 2090-12-31 23:59:59
      if (i?.ads?.length > 0) {
        for (let ii of i.ads) {
          ii.start_time = 3818332800; // Unix 时间戳 2090-12-31 00:00:00
          ii.end_time = 3818419199; // Unix 时间戳 2090-12-31 23:59:59
        }
      }
    }
  }
} else if (url.includes("/v2/user/followings/followfeed")) {
  // 关注页信息流 可能感兴趣的人
  if (obj?.data?.items?.length > 0) {
    // 白名单
    obj.data.items = obj.data.items.filter((i) => i?.recommend_reason === "friend_post");
  }
} else if (url.includes("/v3/note/videofeed")) {
  // 信息流 视频
  if (obj?.data?.length > 0) {
    for (let item of obj.data) {
      if (item?.media_save_config) {
        // 水印开关
        item.media_save_config.disable_save = false;
        item.media_save_config.disable_watermark = true;
        item.media_save_config.disable_weibo_cover = true;
      }
      if (item?.share_info?.function_entries?.length > 0) {
        // 下载限制
        const additem = { type: "video_download" };
        let func = item.share_info.function_entries[0];
        if (func?.type !== "video_download") {
          // 向数组开头添加对象
          item.share_info.function_entries.unshift(additem);
        }
      }
    }
  }
} else if (url.includes("/v4/followfeed")) {
  // 关注列表
  if (obj?.data?.items?.length > 0) {
    // recommend_user可能感兴趣的人
    obj.data.items = obj.data.items.filter((i) => !["recommend_user"]?.includes(i?.recommend_reason));
  }
} else if (url.includes("/v4/note/videofeed")) {
  // 信息流 视频
  let newDatas = [];
  let unlockDatas = [];
  if (obj?.data?.length > 0) {
    for (let item of obj.data) {
      if (item?.id !== "" && item?.video_info_v2?.media?.stream?.h265?.[0]?.master_url !== "") {
        let myData = {
          id: item.id,
          url: item.video_info_v2.media.stream.h265[0].master_url
        };
        newDatas.push(myData);
      }
    }
    $persistentStore.write(JSON.stringify(newDatas), "redBookVideoFeed"); // 普通视频 写入持久化存储
  }
  let videoFeedUnlock = JSON.parse($persistentStore.read("redBookVideoFeedUnlock")); // 禁止保存的视频 读取持久化存储
  if (videoFeedUnlock?.notSave === "rucu6") {
    if (obj?.data?.length > 0) {
      for (let item of obj.data) {
        if (item?.id !== "" && item?.video_info_v2?.media?.stream?.h265?.[0]?.master_url !== "") {
          let myData = {
            id: item.id,
            url: item.video_info_v2.media.stream.h265[0].master_url
          };
          unlockDatas.push(myData);
        }
      }
    }
    $persistentStore.write(JSON.stringify(unlockDatas), "redBookVideoFeedUnlock"); // 禁止保存的视频 写入持久化存储
  }
} else if (url.includes("/v5/recommend/user/follow_recommend")) {
  // 用户详情页 你可能感兴趣的人
  if (obj?.data?.title === "你可能感兴趣的人" && obj?.data?.rec_users?.length > 0) {
    obj.data = {};
  }
} else if (url.includes("/v6/homefeed")) {
  if (obj?.data?.length > 0) {
    // 信息流广告
    let newItems = [];
    for (let item of obj.data) {
      if (item?.model_type === "live_v2") {
        // 信息流-直播
        continue;
      } else if (item.hasOwnProperty("ads_info")) {
        // 信息流-赞助
        continue;
      } else if (item.hasOwnProperty("card_icon")) {
        // 信息流-带货
        continue;
      } else if (item?.note_attributes?.includes("goods")) {
        // 信息流-商品
        continue;
      } else {
        if (item?.related_ques) {
          delete item.related_ques;
        }
        newItems.push(item);
      }
    }
    obj.data = newItems;
  }
} else if (url.includes("/v10/note/video/save")) {
  // 视频保存请求
  let videoFeed = JSON.parse($persistentStore.read("redBookVideoFeed")); // 普通视频 读取持久化存储
  let videoFeedUnlock = JSON.parse($persistentStore.read("redBookVideoFeedUnlock")); // 禁止保存的视频 读取持久化存储
  if (obj?.data?.note_id !== "" && videoFeed?.length > 0) {
    for (let item of videoFeed) {
      if (item.id === obj.data.note_id) {
        obj.data.download_url = item.url;
      }
    }
  }
  if (obj?.data?.note_id !== "" && videoFeedUnlock?.length > 0) {
    if (obj?.data?.disable === true && obj?.data?.msg !== "") {
      obj.data.disable = false;
      obj.data.msg = "保存成功! ";
      obj.data.download_url = "";
      for (let item of videoFeedUnlock) {
        if (item.id === obj.data.note_id) {
          obj.data.download_url = item.url;
        }
      }
      // let attach = { openUrl: +obj.data.download_url, clipboard: obj.data.download_url };
      // 弃用上面的写法 使用快捷指令 自动保存至相册
      $notification.post(
        " 🎉🎉🎉 ",
        "小红书无水印地址捕获成功 ",
        "点此通知即可自动保存至相册 ",
        "shortcuts://run-shortcut?name=小红书下载&input=text&text=" + obj.data.download_url
      );
    }
  }
  videoFeedUnlock = { notSave: "rucu6" };
  $persistentStore.write(JSON.stringify(videoFeedUnlock), "redBookVideoFeedUnlock");
} else if (url.includes("/v10/search/notes")) {
  // 搜索结果
  if (obj?.data?.items?.length > 0) {
    obj.data.items = obj.data.items.filter((i) => i?.model_type === "note");
  }
} else {
  $done({});
}

$done({ body: JSON.stringify(obj) });