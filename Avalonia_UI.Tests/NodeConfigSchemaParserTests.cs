using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigSchemaParserTests
{
    [TestMethod]
    public void ParseReturnsSupportedDescriptorForKnownSchema()
    {
        using var document = JsonDocument.Parse(
            """
            {
              "type": "object",
              "properties": {
                "rows": {
                  "type": "integer",
                  "title": "Rows",
                  "required": true,
                  "default": 3,
                  "minimum": 0
                },
                "operator": {
                  "type": "enum",
                  "title": "Operator",
                  "required": true,
                  "enum": ["EQ", "NE"]
                },
                "columns": {
                  "type": "array",
                  "items": {"type": "string"},
                  "description": "Column names"
                }
              }
            }
            """);

        var result = NodeConfigSchemaParser.Parse("1.0", document.RootElement);

        Assert.IsTrue(result.IsSupported);
        Assert.AreEqual("1.0", result.Schema?.Version);
        Assert.AreEqual("object", result.Schema?.Type);
        Assert.AreEqual(3, result.Schema?.Fields.Count);
        Assert.IsEmpty(result.Warnings);

        var rows = result.Schema!.Fields.Single(field => field.Name == "rows");
        Assert.AreEqual(NodeConfigFieldType.Integer, rows.Type);
        Assert.AreEqual("Rows", rows.Title);
        Assert.IsTrue(rows.Required);
        Assert.AreEqual(3, rows.DefaultValue?.GetInt32());
        Assert.AreEqual(0, rows.Minimum);

        var operatorField = result.Schema.Fields.Single(field => field.Name == "operator");
        CollectionAssert.AreEqual(
            new[] { "EQ", "NE" },
            operatorField.EnumValues.ToArray());

        var columns = result.Schema.Fields.Single(field => field.Name == "columns");
        Assert.AreEqual(NodeConfigFieldType.Array, columns.Type);
        Assert.AreEqual("string", columns.ItemType);
        Assert.AreEqual("Column names", columns.Description);
    }

    [TestMethod]
    public void ParseReturnsUnsupportedWhenSchemaIsMissing()
    {
        var result = NodeConfigSchemaParser.Parse("1.0", null);

        Assert.IsFalse(result.IsSupported);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "CONFIG_SCHEMA_MISSING");
    }

    [TestMethod]
    public void ParseReturnsUnsupportedWhenVersionIsUnknown()
    {
        using var document = JsonDocument.Parse("""{"type":"object","properties":{}}""");

        var result = NodeConfigSchemaParser.Parse("2.0", document.RootElement);

        Assert.IsFalse(result.IsSupported);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "CONFIG_SCHEMA_VERSION_UNSUPPORTED");
    }

    [TestMethod]
    public void ParseKeepsSupportedSchemaWhenPropertiesAreMissing()
    {
        using var document = JsonDocument.Parse("""{"type":"object"}""");

        var result = NodeConfigSchemaParser.Parse("1.0", document.RootElement);

        Assert.IsTrue(result.IsSupported);
        Assert.AreEqual(0, result.Schema?.Fields.Count);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "CONFIG_SCHEMA_PROPERTIES_MISSING");
    }

    [TestMethod]
    public void ParseKeepsUnsupportedFieldAndWarningsForInvalidFieldMetadata()
    {
        using var document = JsonDocument.Parse(
            """
            {
              "type": "object",
              "properties": {
                "bad": {
                  "type": "future",
                  "enum": ["A", 2],
                  "items": {}
                }
              }
            }
            """);

        var result = NodeConfigSchemaParser.Parse("1.0", document.RootElement);

        Assert.IsTrue(result.IsSupported);
        var field = result.Schema!.Fields.Single();
        Assert.AreEqual("bad", field.Name);
        Assert.AreEqual(NodeConfigFieldType.Unsupported, field.Type);
        CollectionAssert.Contains(
            field.Warnings.ToArray(),
            "CONFIG_FIELD_TYPE_UNSUPPORTED");
        CollectionAssert.Contains(
            field.Warnings.ToArray(),
            "CONFIG_FIELD_ENUM_INVALID");
        CollectionAssert.Contains(
            field.Warnings.ToArray(),
            "CONFIG_FIELD_ITEMS_TYPE_MISSING");
    }
}
