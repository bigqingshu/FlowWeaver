using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System.Text.Json;
using System.Threading.Tasks;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeDefinitionListItemViewModelTests
{
    [TestMethod]
    public void FormatsPortsAndStableSummaryText()
    {
        var item = new NodeDefinitionListItemViewModel(new NodeDefinitionDto
        {
            NodeType = "FilterRowsNode",
            NodeVersion = "1.0",
            DisplayName = "Filter Rows",
            InputPorts =
            [
                new NodePortDefinitionDto { Name = "in", Required = true },
                new NodePortDefinitionDto { Name = "side", Required = false },
            ],
            OutputPorts =
            [
                new NodePortDefinitionDto { Name = "out", Required = false },
            ],
            ExecutionMode = "PROCESS_POOL",
            DefaultTimeoutSeconds = 60,
            RetrySafe = false,
            UiVisibility = "visible",
            ConfigSchemaVersion = "1.0",
            ConfigSchema = JsonDocument.Parse(
                """
                {
                  "type": "object",
                  "properties": {
                    "field": {"type": "string"},
                    "operator": {"type": "enum", "enum": ["EQ", "NE"]}
                  }
                }
                """).RootElement.Clone(),
        });

        Assert.AreEqual("Filter Rows", item.DisplayNameText);
        Assert.AreEqual("FilterRowsNode@1.0", item.TypeText);
        Assert.AreEqual("in*, side", item.InputPortsText);
        Assert.AreEqual("out", item.OutputPortsText);
        Assert.AreEqual("60s", item.TimeoutText);
        Assert.AreEqual(
            "2 config field(s): field, operator",
            item.ConfigSchemaSummaryText);
    }

    [TestMethod]
    public void FallsBackForMissingOptionalDisplayValues()
    {
        var item = new NodeDefinitionListItemViewModel(new NodeDefinitionDto
        {
            NodeType = "GenerateTestTableNode",
            NodeVersion = "1.0",
            DisplayName = "",
            InputPorts = [],
            OutputPorts = [],
        });

        Assert.AreEqual("GenerateTestTableNode", item.DisplayNameText);
        Assert.AreEqual("-", item.InputPortsText);
        Assert.AreEqual("-", item.OutputPortsText);
        Assert.AreEqual("Config schema unavailable", item.ConfigSchemaSummaryText);
    }

    [TestMethod]
    public async Task LocalizesBuiltInNodeDisplayNameAndConfigSchemaSummary()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var formatter = new DisplayTextFormatter(localizationService);
        var item = new NodeDefinitionListItemViewModel(
            new NodeDefinitionDto
            {
                NodeType = "GenerateTestTableNode",
                NodeVersion = "1.0",
                DisplayName = "Generate Test Table",
                InputPorts = [],
                OutputPorts = [],
                ConfigSchemaVersion = "1.0",
                ConfigSchema = JsonDocument.Parse(
                    """
                    {
                      "type": "object",
                      "properties": {
                        "rows": {"type": "integer", "title": "Rows"},
                        "seed": {"type": "integer", "title": "Seed"}
                      }
                    }
                    """).RootElement.Clone(),
            },
            formatter);

        Assert.AreEqual("生成测试表", item.DisplayNameText);
        Assert.AreEqual("GenerateTestTableNode@1.0", item.TypeText);
        Assert.AreEqual("2 个配置字段：行数, 随机种子", item.ConfigSchemaSummaryText);
    }

    [TestMethod]
    public async Task LocalizesNewBuiltInNodeDisplayNameAndConfigSchemaSummary()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var formatter = new DisplayTextFormatter(localizationService);
        var item = new NodeDefinitionListItemViewModel(
            new NodeDefinitionDto
            {
                NodeType = "SqlMappingNode",
                NodeVersion = "1.0",
                DisplayName = "SQL Mapping",
                InputPorts = [],
                OutputPorts = [],
                ConfigSchemaVersion = "1.0",
                ConfigSchema = JsonDocument.Parse(
                    """
                    {
                      "type": "object",
                      "properties": {
                        "database_path": {"type": "string", "title": "Database Path"},
                        "table_name": {"type": "string", "title": "Table Name"},
                        "query": {"type": "string", "title": "Query"}
                      }
                    }
                    """).RootElement.Clone(),
            },
            formatter);

        Assert.AreEqual("SQL 映射", item.DisplayNameText);
        Assert.AreEqual("3 个配置字段：数据库路径, 表名, 查询语句", item.ConfigSchemaSummaryText);
    }

    [TestMethod]
    public async Task LocalizedDisplayFallsBackToBackendTextForUnknownNodeDefinition()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var formatter = new DisplayTextFormatter(localizationService);
        var item = new NodeDefinitionListItemViewModel(
            new NodeDefinitionDto
            {
                NodeType = "CustomPluginNode",
                NodeVersion = "1.0",
                DisplayName = "Custom Plugin",
                InputPorts = [],
                OutputPorts = [],
                ConfigSchemaVersion = "1.0",
                ConfigSchema = JsonDocument.Parse(
                    """
                    {
                      "type": "object",
                      "properties": {
                        "custom": {"type": "string", "title": "Custom Field"}
                      }
                    }
                    """).RootElement.Clone(),
            },
            formatter);

        Assert.AreEqual("Custom Plugin", item.DisplayNameText);
        Assert.AreEqual("1 个配置字段：Custom Field", item.ConfigSchemaSummaryText);
    }
}
