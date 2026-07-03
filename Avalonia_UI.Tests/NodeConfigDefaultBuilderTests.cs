using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigDefaultBuilderTests
{
    [TestMethod]
    public void BuildJsonUsesSchemaDefaultsAndRequiredFallbacks()
    {
        using var document = JsonDocument.Parse(
            """
            {
              "type": "object",
              "properties": {
                "rows": {"type": "integer", "required": true, "default": 3},
                "seed": {"type": "integer", "default": 0},
                "operator": {"type": "enum", "required": true, "enum": ["EQ", "NE"]},
                "field": {"type": "string", "required": true},
                "columns": {"type": "array", "items": {"type": "string"}},
                "enabled": {"type": "boolean", "required": true}
              }
            }
            """);
        var schema = NodeConfigSchemaParser.Parse("1.0", document.RootElement).Schema;

        var json = NodeConfigDefaultBuilder.BuildJson(schema);

        using var config = JsonDocument.Parse(json);
        var root = config.RootElement;
        Assert.AreEqual(3, root.GetProperty("rows").GetInt32());
        Assert.AreEqual(0, root.GetProperty("seed").GetInt32());
        Assert.AreEqual("EQ", root.GetProperty("operator").GetString());
        Assert.AreEqual(string.Empty, root.GetProperty("field").GetString());
        Assert.IsFalse(root.GetProperty("enabled").GetBoolean());
        Assert.IsFalse(root.TryGetProperty("columns", out _));
    }

    [TestMethod]
    public void BuildJsonReturnsEmptyObjectForUnsupportedSchema()
    {
        var json = NodeConfigDefaultBuilder.BuildJson(null);

        Assert.AreEqual("{}", json);
    }
}
