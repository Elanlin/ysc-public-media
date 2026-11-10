var catalogUrl = "";
var catalogCache = null;
var pageSize = 20;

function asString(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function loadCatalog() {
  if (catalogCache) return catalogCache;
  if (!catalogUrl) throw new Error("未设置开放媒体目录地址");
  var response = req(catalogUrl, {
    headers: { "User-Agent": "Mozilla/5.0" },
    timeout: 20000
  });
  if (!response || response.code < 200 || response.code >= 300) {
    throw new Error("目录请求失败：" + (response ? response.code : "unknown"));
  }
  catalogCache = JSON.parse(response.content);
  return catalogCache;
}

function simpleVod(item) {
  return {
    vod_id: item.id,
    vod_name: item.name,
    vod_pic: item.pic || "",
    vod_remarks: item.remarks || item.source || "开放媒体"
  };
}

function findItem(id) {
  var items = loadCatalog().items || [];
  for (var i = 0; i < items.length; i += 1) {
    if (asString(items[i].id) === asString(id)) return items[i];
  }
  return null;
}

function responseJson(value) {
  return JSON.stringify(value);
}

export default {
  init: function (ext) {
    catalogCache = null;
    if (typeof ext === "string") {
      try {
        var parsed = JSON.parse(ext);
        catalogUrl = parsed.catalog || parsed.url || ext;
      } catch (e) {
        catalogUrl = ext;
      }
    } else if (ext) {
      catalogUrl = ext.catalog || ext.url || "";
    }
  },

  home: function () {
    var data = loadCatalog();
    var classes = [];
    var categories = data.categories || [];
    for (var i = 0; i < categories.length; i += 1) {
      classes.push({ type_id: categories[i].id, type_name: categories[i].name });
    }
    return responseJson({
      code: 1,
      class: classes,
      list: (data.items || []).slice(0, pageSize).map(simpleVod)
    });
  },

  homeVod: function () {
    return responseJson({
      code: 1,
      list: (loadCatalog().items || []).slice(0, pageSize).map(simpleVod)
    });
  },

  category: function (tid, pg) {
    var page = Math.max(parseInt(pg || "1", 10), 1);
    var all = loadCatalog().items || [];
    var matches = [];
    for (var i = 0; i < all.length; i += 1) {
      if (asString(all[i].category) === asString(tid)) matches.push(all[i]);
    }
    var pages = Math.max(Math.ceil(matches.length / pageSize), 1);
    var start = (page - 1) * pageSize;
    return responseJson({
      code: 1,
      page: page,
      pagecount: pages,
      limit: pageSize,
      total: matches.length,
      list: matches.slice(start, start + pageSize).map(simpleVod)
    });
  },

  detail: function (id) {
    var item = findItem(id);
    if (!item) return responseJson({ code: 1, list: [] });
    var details = [
      item.content || "",
      "来源：" + (item.source || ""),
      "许可：" + (item.license || ""),
      "原始页面：" + (item.detail_url || "")
    ];
    return responseJson({
      code: 1,
      list: [{
        vod_id: item.id,
        vod_name: item.name,
        vod_pic: item.pic || "",
        vod_year: item.year || "",
        vod_area: item.area || "",
        vod_remarks: item.remarks || "",
        vod_director: item.director || "",
        vod_actor: item.actor || "",
        vod_content: details.join("\n"),
        vod_play_from: "官方直链",
        vod_play_url: "播放$" + item.play_url
      }]
    });
  },

  search: function (key, quick, pg) {
    var keyword = asString(key).toLowerCase();
    var page = Math.max(parseInt(pg || "1", 10), 1);
    var all = loadCatalog().items || [];
    var matches = [];
    for (var i = 0; i < all.length; i += 1) {
      var text = [all[i].name, all[i].content, all[i].director, all[i].source]
        .join(" ").toLowerCase();
      if (text.indexOf(keyword) >= 0) matches.push(all[i]);
    }
    var pages = Math.max(Math.ceil(matches.length / pageSize), 1);
    var start = (page - 1) * pageSize;
    return responseJson({
      code: 1,
      page: page,
      pagecount: pages,
      limit: pageSize,
      total: matches.length,
      list: matches.slice(start, start + pageSize).map(simpleVod)
    });
  },

  play: function (flag, id) {
    return responseJson({
      code: 1,
      parse: 0,
      jx: 0,
      url: id,
      header: { "User-Agent": "Mozilla/5.0" }
    });
  },

  destroy: function () {
    catalogCache = null;
  }
};
