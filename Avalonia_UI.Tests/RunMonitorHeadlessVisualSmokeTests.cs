using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Markup.Xaml.Styling;
using Avalonia.Styling;
using Avalonia.Themes.Fluent;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Avalonia_UI.Views.Pages;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RunMonitorHeadlessVisualSmokeTests
{
    [TestMethod]
    public async Task RunMonitorRendersAtDesktopViewportsInChineseAndEnglish()
    {
        var results = new List<RenderSmokeResult>();
        using (var session = HeadlessUnitTestSession.StartNew(
                   typeof(RunMonitorHeadlessAppBuilder)))
        {
            await session.Dispatch(
                async () =>
                {
                    results.Add(await RenderCaseAsync(
                        width: 1093,
                        height: 614,
                        languageCode: "en-US",
                        showLoopMonitor: true));
                    results.Add(await RenderCaseAsync(
                        width: 1366,
                        height: 768,
                        languageCode: "zh-Hans",
                        showLoopMonitor: true));
                    results.Add(await RenderCaseAsync(
                        width: 1920,
                        height: 1080,
                        languageCode: "en-US",
                        showLoopMonitor: false));
                    return true;
                },
                CancellationToken.None);
        }

        Assert.HasCount(3, results);
        foreach (var result in results)
        {
            Assert.IsNull(result.Error, result.Error);
            Assert.IsTrue(result.FrameCaptured, $"No frame was rendered: {result.CaseName}");
            Assert.AreEqual(result.ClientWidth, (double)result.FrameWidth, 8.0);
            Assert.AreEqual(result.ClientHeight, (double)result.FrameHeight, 8.0);
            Assert.IsGreaterThan(
                10_000L,
                result.OutputLength,
                $"Rendered frame looks blank: {result.OutputPath}");
            foreach (var button in result.Buttons)
            {
                Assert.AreEqual(1, button.MatchCount, $"Unexpected {button.Description} count.");
                Assert.IsGreaterThan(0.0, button.Width, $"{button.Description} has no width.");
                Assert.IsGreaterThan(0.0, button.Height, $"{button.Description} has no height.");
                Assert.IsGreaterThanOrEqualTo(-1.0, button.X, $"{button.Description} overflows left.");
                Assert.IsGreaterThanOrEqualTo(-1.0, button.Y, $"{button.Description} overflows top.");
                Assert.IsLessThanOrEqualTo(
                    result.ClientWidth + 1,
                    button.Right,
                    $"{button.Description} overflows right.");
                Assert.IsLessThanOrEqualTo(
                    result.ClientHeight + 1,
                    button.Bottom,
                    $"{button.Description} overflows bottom.");
            }
        }
    }

    private static async Task<RenderSmokeResult> RenderCaseAsync(
        int width,
        int height,
        string languageCode,
        bool showLoopMonitor)
    {
        Window? window = null;
        try
        {
            var localizationService = new JsonLocalizationService();
            await localizationService.SetLanguageAsync(languageCode);
            var apiClient = new EngineHostApiClient();
            var viewModel = new MainWindowViewModel(
                new EngineHostHealthClient(apiClient),
                apiClient,
                new EngineHostRuntimeEventStreamClient(),
                localizationService: localizationService);
            SeedRunMonitor(viewModel, localizationService, showLoopMonitor);

            var page = new RunMonitorPage
            {
                DataContext = viewModel,
            };
            window = new Window
            {
                Width = width,
                Height = height,
                Content = page,
            };
            window.Show();
            Dispatcher.UIThread.RunJobs();
            page.InvalidateVisual();
            window.InvalidateVisual();
            AvaloniaHeadlessPlatform.ForceRenderTimerTick(2);

            var outputPath = Path.Combine(
                Path.GetTempPath(),
                $"FlowWeaver_RunMonitor_{width}x{height}_{languageCode}.png");
            var frame = window.CaptureRenderedFrame();
            var frameCaptured = frame is not null;
            var frameWidth = frame?.PixelSize.Width ?? 0;
            var frameHeight = frame?.PixelSize.Height ?? 0;
            if (frame is not null)
            {
                using (frame)
                {
                    frame.Save(outputPath);
                }
            }

            var buttons = new List<ButtonMeasurement>
            {
                MeasureCommandButton(
                    page,
                    window,
                    viewModel.BackgroundRunManagement.StartCommand,
                    "background start"),
                MeasureCommandButton(
                    page,
                    window,
                    viewModel.BackgroundRunManagement.PreviousPageCommand,
                    "previous page"),
                MeasureCommandButton(
                    page,
                    window,
                    viewModel.BackgroundRunManagement.NextPageCommand,
                    "next page"),
                MeasureCommandButton(
                    page,
                    window,
                    viewModel.NodeRunMonitor.PreviousPageCommand,
                    "node previous page"),
                MeasureCommandButton(
                    page,
                    window,
                    viewModel.NodeRunMonitor.NextPageCommand,
                    "node next page"),
            };
            if (showLoopMonitor)
            {
                buttons.Add(MeasureCommandButton(
                    page,
                    window,
                    viewModel.RunLoopMonitor.LoadMoreLoopsCommand,
                    "loop next page"));
                buttons.Add(MeasureCommandButton(
                    page,
                    window,
                    viewModel.RunLoopMonitor.LoadMoreIterationsCommand,
                    "iteration next page"));
            }
            return new RenderSmokeResult(
                $"{languageCode} {width}x{height}",
                window.ClientSize.Width,
                window.ClientSize.Height,
                frameCaptured,
                frameWidth,
                frameHeight,
                outputPath,
                File.Exists(outputPath) ? new FileInfo(outputPath).Length : 0,
                buttons,
                null);
        }
        catch (Exception exception)
        {
            return new RenderSmokeResult(
                $"{languageCode} {width}x{height}",
                window?.ClientSize.Width ?? 0,
                window?.ClientSize.Height ?? 0,
                false,
                0,
                0,
                string.Empty,
                0,
                [],
                exception.ToString());
        }
        finally
        {
            window?.Close();
        }
    }

    private static void SeedRunMonitor(
        MainWindowViewModel viewModel,
        JsonLocalizationService localizationService,
        bool showLoopMonitor)
    {
        var formatter = new DisplayTextFormatter(localizationService);
        viewModel.BackgroundRunManagement.SetContext(
            new EngineHostConnectionSettings
            {
                Token = "visual-smoke",
            },
            "workflow-visual-smoke",
            canUseActions: true);
        viewModel.BackgroundRunManagement.SetStartTargetNodes(
        [
            new("source", "source / Generate Test Table"),
            new("transform_with_a_long_identifier", "transform_with_a_long_identifier / Filter Rows"),
            new("sink", "sink / Save Table"),
        ],
        definitionLoaded: true);
        if (showLoopMonitor)
        {
            viewModel.BackgroundRunManagement.UsePreviewToNodeStartModeCommand.Execute(null);
            viewModel.BackgroundRunManagement.SelectedStartTargetNode =
                viewModel.BackgroundRunManagement.StartTargetNodes[1];
            viewModel.SelectedRunMonitorTabIndex = 1;
        }

        foreach (var index in Enumerable.Range(0, BackgroundRunManagementViewModel.PageSize))
        {
            viewModel.BackgroundRunManagement.Runs.Add(
                new WorkflowRunListItemViewModel(
                    new WorkflowRunDto
                    {
                        WorkflowRunId = $"run-{index:000}-with-a-long-diagnostic-identifier",
                        WorkflowId = "workflow-visual-smoke",
                        RevisionId = "revision-visual-smoke",
                        WorkflowVersion = 7,
                        Status = (index % 4) switch
                        {
                            0 => "RUNNING",
                            1 => "SUCCEEDED",
                            2 => "FAILED",
                            _ => "CANCELLED",
                        },
                        RunMode = index % 2 == 0 ? "full" : "preview_to_node",
                        TriggerSource = "background_manual",
                        TargetNodeInstanceId = index % 2 == 0 ? null : "transform_with_a_long_identifier",
                        StartedAt = DateTimeOffset.UtcNow.AddMinutes(-index - 1),
                        FinishedAt = index % 4 == 0 ? null : DateTimeOffset.UtcNow,
                        CompletionReason = index % 4 == 2
                            ? "A deliberately long failure reason used to verify text trimming and wrapping."
                            : "completed",
                    },
                    localizationService.GetString,
                    formatter));
        }

        viewModel.BackgroundRunManagement.HasNextPage = true;
        foreach (var index in Enumerable.Range(0, 101))
        {
            viewModel.NodeRunMonitor.Nodes.Add(
                new NodeRunListItemViewModel(
                    new NodeRunDto
                    {
                        NodeRunId = $"node-run-{index:000}",
                        WorkflowRunId = "run-000-with-a-long-diagnostic-identifier",
                        NodeInstanceId = $"node_{index:000}_with_a_long_identifier",
                        NodeType = "FilterRowsNode",
                        Status = index % 3 == 0 ? "RUNNING" : "SUCCEEDED",
                        StateVersion = index + 1,
                        ExecutorId = "executor-visual-smoke",
                        Progress = index % 3 == 0 ? 0.5 : 1.0,
                        CurrentStage = "processing_rows",
                        Attempt = 1,
                        StartedAt = DateTimeOffset.UtcNow.AddSeconds(-30),
                    },
                    formatter));
        }

        viewModel.NodeRunMonitor.Total = 101;
        viewModel.NodeRunMonitor.HasNextPage = true;

        var startedAt = DateTimeOffset.UtcNow.AddMinutes(-5);
        var loop = new LoopRunListItemViewModel(
            new LoopRunDto
            {
                LoopRunId = "loop-run-visual-smoke-with-a-long-identifier",
                WorkflowRunId = "run-000-with-a-long-diagnostic-identifier",
                LoopId = "validation_loop",
                StartNodeInstanceId = "source",
                JudgeNodeInstanceId = "judge_with_a_long_identifier",
                Status = "MAX_ITERATIONS_REACHED",
                CurrentIteration = 20,
                MaxIterations = 20,
                ExitReason = "MAX_ITERATIONS_REACHED",
                StartedAt = startedAt,
                FinishedAt = startedAt.AddMinutes(5),
                Error = Json(
                    "{\"code\":\"LOOP_LIMIT\",\"message\":\"A long diagnostic message verifies wrapping without expanding the page beyond its viewport.\"}"),
            },
            formatter);
        viewModel.RunLoopMonitor.Loops.Add(loop);
        viewModel.RunLoopMonitor.SelectedLoop = loop;
    }

    private static ButtonMeasurement MeasureCommandButton(
        Control root,
        Window window,
        System.Windows.Input.ICommand command,
        string description)
    {
        var buttons = root
            .GetVisualDescendants()
            .OfType<Button>()
            .Where(candidate => ReferenceEquals(candidate.Command, command))
            .ToArray();
        if (buttons.Length != 1)
        {
            return new ButtonMeasurement(description, buttons.Length, 0, 0, 0, 0, 0, 0);
        }

        var button = buttons[0];
        var origin = button.TranslatePoint(new Point(0, 0), window);
        if (origin is null)
        {
            return new ButtonMeasurement(description, 1, button.Bounds.Width, button.Bounds.Height, 0, 0, 0, 0);
        }

        return new ButtonMeasurement(
            description,
            1,
            button.Bounds.Width,
            button.Bounds.Height,
            origin.Value.X,
            origin.Value.Y,
            origin.Value.X + button.Bounds.Width,
            origin.Value.Y + button.Bounds.Height);
    }

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }

    private sealed record RenderSmokeResult(
        string CaseName,
        double ClientWidth,
        double ClientHeight,
        bool FrameCaptured,
        int FrameWidth,
        int FrameHeight,
        string OutputPath,
        long OutputLength,
        IReadOnlyList<ButtonMeasurement> Buttons,
        string? Error);

    private sealed record ButtonMeasurement(
        string Description,
        int MatchCount,
        double Width,
        double Height,
        double X,
        double Y,
        double Right,
        double Bottom);
}

public static class RunMonitorHeadlessAppBuilder
{
    public static AppBuilder BuildAvaloniaApp()
    {
        return AppBuilder.Configure<RunMonitorHeadlessApplication>()
            .UseSkia()
            .UseHeadless(new AvaloniaHeadlessPlatformOptions
            {
                UseHeadlessDrawing = false,
            });
    }
}

public sealed class RunMonitorHeadlessApplication : Application
{
    public override void Initialize()
    {
        RequestedThemeVariant = ThemeVariant.Light;
        Resources.MergedDictionaries.Add(
            new ResourceInclude(new Uri("avares://Avalonia_UI/"))
            {
                Source = new Uri("avares://Avalonia_UI/Styles/ColorPalette.axaml"),
            });
        Styles.Add(new FluentTheme());
        Styles.Add(
            new StyleInclude(new Uri("avares://Avalonia_UI/"))
            {
                Source = new Uri("avares://Avalonia_UI/Styles/ControlStyles.axaml"),
            });
    }
}
