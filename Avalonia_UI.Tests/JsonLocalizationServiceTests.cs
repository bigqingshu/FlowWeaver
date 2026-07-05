using System;
using System.IO;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class JsonLocalizationServiceTests
{
    [TestMethod]
    public async Task SetLanguageLoadsEnglishStrings()
    {
        var service = new JsonLocalizationService(CreateLocalizationDirectory());

        await service.SetLanguageAsync("en-US");

        Assert.AreEqual("en-US", service.CurrentLanguageCode);
        Assert.AreEqual("Base URL", service.GetString("connection.base_url"));
        Assert.AreEqual(
            "A node with this instance ID already exists.",
            service.GetString("definition.warning.node_already_exists"));
        Assert.AreEqual("missing.key", service.GetString("missing.key"));
    }

    [TestMethod]
    public async Task SetLanguageLoadsSimplifiedChineseStrings()
    {
        var service = new JsonLocalizationService(CreateLocalizationDirectory());

        await service.SetLanguageAsync("zh-Hans");

        Assert.AreEqual("zh-Hans", service.CurrentLanguageCode);
        Assert.AreEqual("服务地址", service.GetString("connection.base_url"));
        Assert.AreEqual("关闭", service.GetString("common.close"));
        Assert.AreEqual("简体中文", service.GetString("language.zh-Hans"));
        Assert.AreEqual(
            "当前有未保存草稿；运行和预览会先保存草稿并使用最新版本。",
            service.GetString("workflow.run_guard_dirty_draft"));
        Assert.AreEqual("尚未加载数据预览。", service.GetString("data_preview.source_not_loaded"));
        Assert.AreEqual(
            "来源：完整运行 run-1，节点 generate，表 orders。",
            service.Format("format.data_preview_source_full", "run-1", "generate", "orders"));
        Assert.AreEqual(
            "来源：预览运行 run-preview 到节点 generate，表 orders。",
            service.Format(
                "format.data_preview_source_preview",
                "run-preview",
                "generate",
                "orders"));
        Assert.AreEqual(
            "请先删除相关连接，再删除该节点。",
            service.GetString("definition.warning.node_has_connections"));
        Assert.AreEqual(
            "在草稿中未找到选中的插入位置节点。",
            service.GetString("definition.warning.insert_after_node_not_found"));
        Assert.AreEqual(
            "节点已添加到草稿，并已更新线性连接。保存前请重新校验。",
            service.GetString("definition.node_added_with_connections"));
        Assert.AreEqual("列表上移", service.GetString("definition.move_node_up"));
        Assert.AreEqual("列表下移", service.GetString("definition.move_node_down"));
        Assert.AreEqual(
            "节点列表顺序已更新，连接未改变。保存前请重新校验。",
            service.GetString("definition.node_moved"));
        Assert.AreEqual(
            "节点列表顺序已更新，并已重排线性连接。保存前请重新校验。",
            service.GetString("definition.node_moved_with_rewired_connections"));
        Assert.AreEqual(
            "已更新连接：\n移除：\n- old\n新增：\n- new",
            service.Format(
                "definition.node_move_rewired_connections",
                "- old",
                "- new"));
        Assert.AreEqual(
            "已识别为线性链路：3 个节点。支持的删除/移动操作可自动维护连接。",
            service.Format("definition.linear_chain_status_linear", 3));
        Assert.AreEqual(
            "当前不是受支持的线性链路：存在一个节点连接到多个下游节点。",
            service.Format(
                "definition.linear_chain_status_not_linear",
                service.GetString("definition.warning.linear_chain_branching")));
        Assert.AreEqual("复制节点", service.GetString("definition.copy_node"));
        Assert.AreEqual("删除已选", service.GetString("definition.delete_selected_nodes"));
        Assert.AreEqual(
            "已选择 2 个节点",
            service.Format("definition.batch_selected_nodes", 2));
        Assert.AreEqual(
            "已从草稿删除 2 个节点。保存前请重新校验。",
            service.Format("format.workflow_definition_nodes_deleted", 2));
        Assert.AreEqual(
            "已从草稿删除 2 个节点，并同步移除相关连接。保存前请重新校验。",
            service.Format("format.workflow_definition_nodes_deleted_with_connections", 2));
        Assert.AreEqual(
            "节点已复制到草稿。保存前请重新校验。",
            service.GetString("definition.node_copied"));
        Assert.AreEqual(
            "所选节点无法继续向该方向移动。",
            service.GetString("definition.warning.node_move_out_of_range"));
        Assert.AreEqual(
            "已更新连接：\n移除：\n- old\n新增：\n- new",
            service.Format(
                "definition.node_add_rewired_connections",
                "- old",
                "- new"));
        Assert.AreEqual(
            "节点及相关连接已从草稿删除。保存前请重新校验。",
            service.GetString("definition.node_deleted_with_connections"));
        Assert.AreEqual(
            "已同步移除相关连接：\n- c1: source.out -> filter.in",
            service.Format(
                "definition.node_delete_removed_connections",
                "- c1: source.out -> filter.in"));
        Assert.AreEqual(
            "节点已从草稿删除，并已更新线性连接。保存前请重新校验。",
            service.GetString("definition.node_deleted_with_rewired_connections"));
        Assert.AreEqual(
            "已更新连接：\n移除：\n- old\n新增：\n- new",
            service.Format(
                "definition.node_delete_rewired_connections",
                "- old",
                "- new"));
    }

    [TestMethod]
    public async Task UnsupportedLanguageFallsBackToEnglish()
    {
        var service = new JsonLocalizationService(CreateLocalizationDirectory());

        await service.SetLanguageAsync("fr-FR");

        Assert.AreEqual("en-US", service.CurrentLanguageCode);
        Assert.AreEqual("Base URL", service.GetString("connection.base_url"));
    }

    [TestMethod]
    public async Task MissingLocalizedKeyFallsBackToEnglish()
    {
        var localizationDirectory = CreateLocalizationDirectory();
        await File.WriteAllTextAsync(
            Path.Combine(localizationDirectory, "zh-Hans.json"),
            """
            {
              "connection.base_url": "服务地址"
            }
            """);
        var service = new JsonLocalizationService(localizationDirectory);

        await service.SetLanguageAsync("zh-Hans");

        Assert.AreEqual("服务地址", service.GetString("connection.base_url"));
        Assert.AreEqual("Check", service.GetString("connection.check"));
    }

    [TestMethod]
    public async Task FormatUsesLocalizedTemplate()
    {
        var service = new JsonLocalizationService(CreateLocalizationDirectory());
        await service.SetLanguageAsync("zh-Hans");

        var message = service.Format("format.loaded_workflows", 3);

        Assert.AreEqual("已加载 3 个工作流。", message);
    }

    [TestMethod]
    public async Task DefaultLocalizationDirectoryCanLoadCopiedResources()
    {
        var service = new JsonLocalizationService();

        await service.SetLanguageAsync("zh-Hans");

        Assert.AreEqual("zh-Hans", service.CurrentLanguageCode);
        Assert.AreEqual("服务地址", service.GetString("connection.base_url"));
    }

    private static string CreateLocalizationDirectory()
    {
        var repoRoot = FindRepoRoot();
        var sourceDirectory = Path.Combine(repoRoot, "Avalonia_UI", "Localization");
        var targetDirectory = Path.Combine(
            Path.GetTempPath(),
            "FlowWeaverTests",
            Guid.NewGuid().ToString("N"),
            "Localization");
        Directory.CreateDirectory(targetDirectory);
        foreach (var file in Directory.GetFiles(sourceDirectory, "*.json"))
        {
            File.Copy(file, Path.Combine(targetDirectory, Path.GetFileName(file)));
        }

        return targetDirectory;
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "pyproject.toml"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
