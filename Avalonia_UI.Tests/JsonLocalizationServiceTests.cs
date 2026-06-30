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
        Assert.AreEqual("missing.key", service.GetString("missing.key"));
    }

    [TestMethod]
    public async Task SetLanguageLoadsSimplifiedChineseStrings()
    {
        var service = new JsonLocalizationService(CreateLocalizationDirectory());

        await service.SetLanguageAsync("zh-Hans");

        Assert.AreEqual("zh-Hans", service.CurrentLanguageCode);
        Assert.AreEqual("服务地址", service.GetString("connection.base_url"));
        Assert.AreEqual("简体中文", service.GetString("language.zh-Hans"));
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
