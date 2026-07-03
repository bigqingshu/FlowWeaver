using System;
using System.Collections;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Headless;
using Avalonia.Threading;
using Avalonia.VisualTree;
using Avalonia_UI;
using Avalonia_UI.Api;
using Avalonia_UI.ViewModels;
using Avalonia_UI.Views.Components.Workflow;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewHeadlessSmokeTests
{
    [TestMethod]
    public async Task WorkflowSummaryViewLoadsStructuredEditBindingsInHeadlessRuntime()
    {
        using var session = HeadlessUnitTestSession.StartNew(
            typeof(WorkflowSummaryViewHeadlessTestAppBuilder),
            AvaloniaTestIsolationLevel.PerTest);

        await session.Dispatch(
            () =>
            {
                var viewModel = CreateViewModel();
                viewModel.IsWorkflowConnectionsAdvancedVisible = true;
                var view = new WorkflowSummaryView
                {
                    DataContext = viewModel,
                };
                var window = new Window
                {
                    Width = 1200,
                    Height = 900,
                    Content = view,
                };

                try
                {
                    window.Show();
                    Dispatcher.UIThread.RunJobs();
                    AvaloniaHeadlessPlatform.ForceRenderTimerTick();

                    var comboBoxes = view
                        .GetVisualDescendants()
                        .OfType<ComboBox>()
                        .ToArray();

                    Assert.IsGreaterThanOrEqualTo(
                        1,
                        comboBoxes.Length,
                        "WorkflowSummaryView should materialize the add-node ComboBox control.");
                    Assert.IsTrue(
                        comboBoxes.Any(combo =>
                            ReferenceEquals(combo.ItemsSource, viewModel.NodeDefinitions)
                            && CountItems(combo.ItemsSource) == 1),
                        "The new node type ComboBox should bind to NodeDefinitions.");
                    Assert.AreEqual(
                        0,
                        comboBoxes.Count(combo =>
                            !ReferenceEquals(combo.ItemsSource, viewModel.NodeDefinitions)
                            && CountItems(combo.ItemsSource) == 2),
                        "The read-only connection section should not materialize source or target node ComboBoxes.");
                }
                finally
                {
                    window.Close();
                }
            },
            CancellationToken.None);
    }

    private static MainWindowViewModel CreateViewModel()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "display_name": "Source",
                  "config": {}
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "display_name": "Filter",
                  "config": {}
                }
              ],
              "connections": [
                {
                  "connection_id": "source_to_filter",
                  "source_node_id": "source",
                  "source_port": "rows",
                  "target_node_id": "filter",
                  "target_port": "rows"
                }
              ]
            }
            """;
        var definition = JsonSerializer.Deserialize<JsonElement>(definitionJson);
        var viewModel = new MainWindowViewModel();
        viewModel.NodeDefinitions.Add(
            new NodeDefinitionListItemViewModel(
                new NodeDefinitionDto
                {
                    NodeType = "GenerateTestTableNode",
                    NodeVersion = "1.0",
                    DisplayName = "Generate table",
                    OutputPorts =
                    [
                        new NodePortDefinitionDto
                        {
                            Name = "rows",
                            Required = true,
                        },
                    ],
                    ExecutionMode = "immediate",
                    DefaultTimeoutSeconds = 30,
                    RetrySafe = true,
                    UiVisibility = "visible",
                }));
        viewModel.WorkflowDefinitionDetail = new WorkflowDefinitionDetailViewModel(
            new WorkflowDefinitionDto
            {
                WorkflowId = "wf-smoke",
                Name = "Smoke workflow",
                RevisionId = "rev-1",
                Version = 1,
                DefinitionHash = "hash",
                Definition = definition,
                Status = "ACTIVE",
                UpdatedAt = DateTimeOffset.UtcNow,
            },
            []);
        viewModel.WorkflowDefinitionDraftJson = definitionJson;

        return viewModel;
    }

    private static int CountItems(object? itemsSource)
    {
        if (itemsSource is null)
        {
            return 0;
        }

        if (itemsSource is ICollection collection)
        {
            return collection.Count;
        }

        return itemsSource is IEnumerable enumerable
            ? enumerable.Cast<object>().Count()
            : 0;
    }
}

public static class WorkflowSummaryViewHeadlessTestAppBuilder
{
    public static AppBuilder BuildAvaloniaApp()
        => AppBuilder
            .Configure<App>()
            .UseHeadless(
                new AvaloniaHeadlessPlatformOptions
                {
                    UseHeadlessDrawing = true,
                })
            .WithInterFont()
            .LogToTrace();
}
