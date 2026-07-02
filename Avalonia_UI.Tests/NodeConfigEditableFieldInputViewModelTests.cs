using System.Linq;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigEditableFieldInputViewModelTests
{
    [TestMethod]
    public void InputFieldTracksDirtyStateAndBuildsEditableDraftField()
    {
        var field = new NodeConfigEditableDraftField
        {
            Name = "operator",
            Type = NodeConfigFieldType.Enum,
            Title = "Operator",
            Required = true,
            InputValue = "GT",
            HasInputValue = true,
            EnumValues = ["GT", "LT"],
            Warnings = ["CONFIG_DRAFT_FIELD_REQUIRED_MISSING"],
        };

        var input = new NodeConfigEditableFieldInputViewModel(field);

        Assert.AreEqual("operator", input.Name);
        Assert.AreEqual("GT", input.InputValue);
        Assert.IsTrue(input.HasInputValue);
        Assert.IsFalse(input.IsDirty);

        input.InputValue = "LT";

        Assert.IsTrue(input.HasInputValue);
        Assert.IsTrue(input.IsDirty);

        var updated = input.ToEditableDraftField();
        Assert.AreEqual("operator", updated.Name);
        Assert.AreEqual("LT", updated.InputValue);
        Assert.IsTrue(updated.HasInputValue);
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            updated.EnumValues.ToArray());
        CollectionAssert.Contains(
            updated.Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_REQUIRED_MISSING");
    }
}
