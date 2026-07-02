using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigEditableDraftBuilderTests
{
    [TestMethod]
    public void BuildCreatesEditableFieldsFromSupportedDraft()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "field": {"type": "string", "title": "Field"},
                "limit": {"type": "integer", "title": "Limit"},
                "ratio": {"type": "number", "title": "Ratio"},
                "enabled": {"type": "boolean", "title": "Enabled"},
                "operator": {"type": "enum", "title": "Operator", "enum": ["GT", "LT"]},
                "columns": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"}
              }
            }
            """);
        var draft = NodeConfigDraftBuilder.Build(
            """
            {
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "config": {
                    "field": "amount",
                    "limit": 3,
                    "ratio": 1.5,
                    "enabled": false,
                    "operator": "GT",
                    "columns": ["amount"],
                    "metadata": {"owner": "tester"}
                  }
                }
              ]
            }
            """,
            "filter",
            schema);

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);

        Assert.AreEqual("filter", editableDraft.NodeInstanceId);
        Assert.IsTrue(editableDraft.HasFields);
        Assert.HasCount(5, editableDraft.Fields);
        Assert.IsEmpty(editableDraft.Warnings);

        Assert.AreEqual(
            "amount",
            editableDraft.Fields.Single(field => field.Name == "field").InputValue);
        Assert.AreEqual(
            "3",
            editableDraft.Fields.Single(field => field.Name == "limit").InputValue);
        Assert.AreEqual(
            "1.5",
            editableDraft.Fields.Single(field => field.Name == "ratio").InputValue);
        Assert.AreEqual(
            "false",
            editableDraft.Fields.Single(field => field.Name == "enabled").InputValue);

        var enumField = editableDraft.Fields.Single(field => field.Name == "operator");
        Assert.AreEqual(NodeConfigFieldType.Enum, enumField.Type);
        Assert.AreEqual("GT", enumField.InputValue);
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            enumField.EnumValues.ToArray());

        Assert.IsFalse(editableDraft.Fields.Any(field => field.Name == "columns"));
        Assert.IsFalse(editableDraft.Fields.Any(field => field.Name == "metadata"));
    }

    [TestMethod]
    public void BuildUsesDefaultWhenCurrentValueIsMissing()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "limit": {"type": "integer", "default": 10},
                "enabled": {"type": "boolean", "default": true}
              }
            }
            """);
        var draft = NodeConfigDraftBuilder.Build(
            """{"nodes":[{"node_instance_id":"filter","config":{}}]}""",
            "filter",
            schema);

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);

        Assert.AreEqual(
            "10",
            editableDraft.Fields.Single(field => field.Name == "limit").InputValue);
        Assert.AreEqual(
            "true",
            editableDraft.Fields.Single(field => field.Name == "enabled").InputValue);
    }

    [TestMethod]
    public void BuildCarriesEditableFieldWarnings()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "field": {"type": "string", "required": true}
              }
            }
            """);
        var draft = NodeConfigDraftBuilder.Build(
            """{"nodes":[{"node_instance_id":"filter","config":{}}]}""",
            "filter",
            schema);

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);

        var field = editableDraft.Fields.Single();
        Assert.AreEqual(string.Empty, field.InputValue);
        CollectionAssert.Contains(
            field.Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_REQUIRED_MISSING");
    }

    [TestMethod]
    public void BuildReturnsNoEditableFieldsWarningWhenAllFieldsRequireJsonFallback()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "columns": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"}
              }
            }
            """);
        var draft = NodeConfigDraftBuilder.Build(
            """{"nodes":[{"node_instance_id":"filter","config":{}}]}""",
            "filter",
            schema);

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);

        Assert.IsFalse(editableDraft.HasFields);
        Assert.IsEmpty(editableDraft.Fields);
        CollectionAssert.Contains(
            editableDraft.Warnings.ToArray(),
            "EDITABLE_DRAFT_NO_EDITABLE_FIELDS");
    }

    [TestMethod]
    public void BuildCarriesUnsupportedDraftWarnings()
    {
        var draft = new NodeConfigDraft
        {
            NodeInstanceId = "filter",
            Status = NodeConfigDraftStatus.JsonInvalid,
            Warnings = ["CONFIG_DRAFT_JSON_INVALID"],
        };

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);

        Assert.AreEqual("filter", editableDraft.NodeInstanceId);
        Assert.IsFalse(editableDraft.HasFields);
        Assert.IsEmpty(editableDraft.Fields);
        CollectionAssert.Contains(
            editableDraft.Warnings.ToArray(),
            "CONFIG_DRAFT_JSON_INVALID");
    }

    private static NodeConfigSchemaDescriptor ParseSchema(string schemaJson)
    {
        using var document = JsonDocument.Parse(schemaJson);
        var result = NodeConfigSchemaParser.Parse("1.0", document.RootElement);
        Assert.IsTrue(result.IsSupported);
        Assert.IsNotNull(result.Schema);
        return result.Schema;
    }
}
