using Avalonia_UI.Api;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeTableOutputTargetViewModelTests
{
    [TestMethod]
    public void NullLogicalTableIdProducesInvalidDraftWithoutThrowing()
    {
        var changedCount = 0;
        var target = new NodeTableOutputTargetViewModel(
            new NodeTableOutputSlotDto
            {
                Name = "out",
                DefaultRole = "AUXILIARY",
                AllowNewMemory = true,
            },
            [],
            draft: null,
            key => key,
            () => changedCount++);

        target.LogicalTableId = null!;

        Assert.IsFalse(target.IsValid);
        Assert.IsNull(target.BuildDraft());
        Assert.AreEqual(1, changedCount);
    }
}
