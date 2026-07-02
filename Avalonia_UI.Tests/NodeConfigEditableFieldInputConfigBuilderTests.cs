using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigEditableFieldInputConfigBuilderTests
{
    [TestMethod]
    public void BuildCreatesConfigJsonFromInputFields()
    {
        var fields = new[]
        {
            InputField("field", NodeConfigFieldType.String, "amount"),
            InputField("limit", NodeConfigFieldType.Integer, "3"),
            InputField("enabled", NodeConfigFieldType.Boolean, "true"),
            InputField("operator", NodeConfigFieldType.Enum, "GT", enumValues: ["GT", "LT"]),
        };

        fields[0].InputValue = "total";

        var result = NodeConfigEditableFieldInputConfigBuilder.Build(
            "filter",
            fields);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.ConfigJson);
        var root = document.RootElement;
        Assert.AreEqual("total", root.GetProperty("field").GetString());
        Assert.AreEqual(3, root.GetProperty("limit").GetInt64());
        Assert.IsTrue(root.GetProperty("enabled").GetBoolean());
        Assert.AreEqual("GT", root.GetProperty("operator").GetString());
    }

    [TestMethod]
    public void BuildReturnsFieldErrorsFromInputFields()
    {
        var fields = new[]
        {
            InputField("limit", NodeConfigFieldType.Integer, "abc"),
            InputField("operator", NodeConfigFieldType.Enum, "NE", enumValues: ["GT", "LT"]),
        };

        var result = NodeConfigEditableFieldInputConfigBuilder.Build(
            "filter",
            fields);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
            result.Status);
        Assert.HasCount(2, result.FieldErrors);
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_INTEGER_INVALID");
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_ENUM_INVALID");
    }

    [TestMethod]
    public void BuildRejectsEmptyInputFieldCollection()
    {
        var result = NodeConfigEditableFieldInputConfigBuilder.Build(
            "filter",
            []);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.DraftUnsupported,
            result.Status);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "EDITABLE_CONFIG_NO_EDITABLE_FIELDS");
    }

    private static NodeConfigEditableFieldInputViewModel InputField(
        string name,
        NodeConfigFieldType type,
        string inputValue,
        string[]? enumValues = null)
    {
        return new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = name,
                Type = type,
                InputValue = inputValue,
                HasInputValue = true,
                EnumValues = enumValues ?? [],
            });
    }
}
