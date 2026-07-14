using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeTableInputBindingViewModelTests
{
    [TestMethod]
    public async Task CurrentTableSourceUsesChineseAndEnglishDisplayTextByDefault()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var input = new NodeTableInputBindingViewModel(
            new NodeTableInputSlotDto
            {
                Name = "main",
                Required = true,
            },
            [],
            draft: null,
            localizationService.GetString,
            new DisplayTextFormatter(localizationService),
            _ => { });

        Assert.AreEqual("当前表 (Current table)", input.Sources[0].DisplayText);
        Assert.AreSame(input.Sources[0], input.SelectedSource);
    }
}
