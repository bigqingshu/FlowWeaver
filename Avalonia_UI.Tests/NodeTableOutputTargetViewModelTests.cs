using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
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
            DisplayTextFormatter.Invariant,
            () => changedCount++);

        target.LogicalTableId = null!;

        Assert.IsFalse(target.IsValid);
        Assert.IsNull(target.BuildDraft());
        Assert.AreEqual(1, changedCount);
    }

    [TestMethod]
    public async Task FixedTargetKindsUseChineseAndEnglishDisplayText()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var target = new NodeTableOutputTargetViewModel(
            new NodeTableOutputSlotDto
            {
                Name = "out",
                DefaultRole = "CURRENT",
                AllowCurrent = true,
                AllowNewMemory = true,
            },
            [],
            draft: null,
            localizationService.GetString,
            new DisplayTextFormatter(localizationService),
            () => { });

        CollectionAssert.AreEqual(
            new[] { "当前表 (Current table)", "新建内存表 (New memory table)" },
            target.TargetKinds.Select(option => option.DisplayText).ToArray());
    }
}
